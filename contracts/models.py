from django.db import models
from django.conf import settings
from django.utils import timezone
import datetime


class ContractCategory(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering    = ["name"]
        verbose_name_plural = "Contract Categories"

    def __str__(self):
        return self.name


class Contract(models.Model):

    class Status(models.TextChoices):
        DRAFT             = "DRAFT",             "Draft"
        UNDER_REVIEW      = "UNDER_REVIEW",      "Under Review"
        PENDING_APPROVAL  = "PENDING_APPROVAL",  "Pending Approval"
        APPROVED          = "APPROVED",          "Approved"
        PENDING_SIGNATURE = "PENDING_SIGNATURE", "Pending Signature"
        ACTIVE            = "ACTIVE",            "Active"
        EXPIRING_SOON     = "EXPIRING_SOON",     "Expiring Soon"
        EXPIRED           = "EXPIRED",           "Expired"
        RENEWED           = "RENEWED",           "Renewed"
        REJECTED          = "REJECTED",          "Rejected"
        CANCELLED         = "CANCELLED",         "Cancelled"
        ARCHIVED          = "ARCHIVED",          "Archived"

    class Priority(models.TextChoices):
        LOW      = "LOW",      "Low"
        MEDIUM   = "MEDIUM",   "Medium"
        HIGH     = "HIGH",     "High"
        CRITICAL = "CRITICAL", "Critical"

    # Identification
    contract_number = models.CharField(max_length=30, unique=True, editable=False)
    title           = models.CharField(max_length=255)
    contract_type   = models.ForeignKey(
        ContractCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contracts",
    )
    description     = models.TextField(blank=True)

    # Party information
    party_name    = models.CharField(max_length=200, verbose_name="Party / Vendor Name")
    party_contact = models.CharField(max_length=200, blank=True, verbose_name="Party Contact Person")
    party_email   = models.EmailField(blank=True, verbose_name="Party Email")
    party_phone   = models.CharField(max_length=30, blank=True, verbose_name="Party Phone")

    # Organisational
    department = models.ForeignKey(
        "accounts.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contracts",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_contracts",
    )

    # Dates
    start_date   = models.DateField()
    end_date     = models.DateField()
    renewal_date = models.DateField(null=True, blank=True)

    # Financial
    contract_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    payment_terms  = models.CharField(max_length=200, blank=True)

    # Status & priority
    status   = models.CharField(max_length=25, choices=Status.choices, default=Status.DRAFT)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)

    # Notes
    notes         = models.TextField(blank=True)
    renewal_terms = models.TextField(blank=True)

    # Meta
    created_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_contracts",
    )
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.contract_number} — {self.title}"

    # ── Contract number generation ──────────────────────────────────────────
    def save(self, *args, **kwargs):
        if not self.contract_number:
            self.contract_number = self._generate_contract_number()
        super().save(*args, **kwargs)

    @classmethod
    def _generate_contract_number(cls):
        year  = timezone.now().year
        last  = cls.objects.filter(contract_number__startswith=f"CTR-{year}-").order_by("contract_number").last()
        if last:
            last_seq = int(last.contract_number.split("-")[-1])
            seq = last_seq + 1
        else:
            seq = 1
        return f"CTR-{year}-{seq:04d}"

    # ── Computed properties ─────────────────────────────────────────────────
    @property
    def days_until_expiry(self):
        if self.end_date:
            delta = self.end_date - timezone.now().date()
            return delta.days
        return None

    @property
    def is_expired(self):
        return self.end_date < timezone.now().date() if self.end_date else False

    @property
    def expiry_urgency(self):
        """Returns 'critical', 'urgent', 'warning', 'normal', or 'expired'."""
        days = self.days_until_expiry
        if days is None:
            return "normal"
        if days < 0:
            return "expired"
        thresholds = settings.RENEWAL_THRESHOLDS
        if days <= thresholds["critical"]:
            return "critical"
        if days <= thresholds["urgent"]:
            return "urgent"
        if days <= thresholds["warning"]:
            return "warning"
        return "normal"

    @property
    def current_version(self):
        return self.versions.order_by("-version_number").first()

    @property
    def status_badge_class(self):
        mapping = {
            "DRAFT":             "secondary",
            "UNDER_REVIEW":      "info",
            "PENDING_APPROVAL":  "warning",
            "APPROVED":          "primary",
            "PENDING_SIGNATURE": "warning",
            "ACTIVE":            "success",
            "EXPIRING_SOON":     "warning",
            "EXPIRED":           "danger",
            "RENEWED":           "success",
            "REJECTED":          "danger",
            "CANCELLED":         "secondary",
            "ARCHIVED":          "secondary",
        }
        return mapping.get(self.status, "secondary")


class ContractVersion(models.Model):
    contract       = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    document       = models.FileField(upload_to="contracts/documents/%Y/%m/", null=True, blank=True)
    change_summary = models.TextField(blank=True, verbose_name="Change Summary / Notes")
    created_by     = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="contract_versions",
    )
    created_at     = models.DateTimeField(auto_now_add=True)
    is_current     = models.BooleanField(default=True)

    class Meta:
        ordering = ["-version_number"]
        unique_together = ("contract", "version_number")

    def __str__(self):
        return f"{self.contract.contract_number} v{self.version_number}"

    def save(self, *args, **kwargs):
        if self.is_current:
            # Mark all other versions as not current
            ContractVersion.objects.filter(
                contract=self.contract
            ).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


class ContractAssignment(models.Model):
    contract   = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="assignments")
    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contract_assignments",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="assignments_made",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    notes       = models.TextField(blank=True)

    class Meta:
        unique_together = ("contract", "user")

    def __str__(self):
        return f"{self.contract.contract_number} → {self.user.username}"
