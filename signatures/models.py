from django.db import models
from django.conf import settings


class Signature(models.Model):

    class Status(models.TextChoices):
        NOT_REQUIRED = "NOT_REQUIRED", "Not Required"
        PENDING      = "PENDING",      "Pending"
        SIGNED       = "SIGNED",       "Signed"
        REJECTED     = "REJECTED",     "Rejected"
        EXPIRED      = "EXPIRED",      "Expired"

    contract         = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.CASCADE,
        related_name="signatures",
    )
    contract_version = models.ForeignKey(
        "contracts.ContractVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="signatures",
    )
    signer           = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="signatures",
    )
    requested_by     = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="signature_requests",
    )
    signature_data   = models.TextField(blank=True, help_text="Base64 encoded signature canvas data")
    status           = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    rejection_reason = models.TextField(blank=True)
    ip_address       = models.GenericIPAddressField(null=True, blank=True)
    requested_at     = models.DateTimeField(auto_now_add=True)
    signed_at        = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.contract.contract_number} — {self.signer} ({self.status})"
