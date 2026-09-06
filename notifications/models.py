from django.db import models
from django.conf import settings
from django.utils import timezone


class Notification(models.Model):

    class NotificationType(models.TextChoices):
        CONTRACT_EXPIRY     = "CONTRACT_EXPIRY",     "Contract Expiry"
        RENEWAL_REMINDER    = "RENEWAL_REMINDER",    "Renewal Reminder"
        APPROVAL_REQUIRED   = "APPROVAL_REQUIRED",   "Approval Required"
        SIGNATURE_REQUIRED  = "SIGNATURE_REQUIRED",  "Signature Required"
        CONTRACT_UPDATED    = "CONTRACT_UPDATED",    "Contract Updated"
        CONTRACT_REJECTED   = "CONTRACT_REJECTED",   "Contract Rejected"
        CONTRACT_APPROVED   = "CONTRACT_APPROVED",   "Contract Approved"
        ASSIGNMENT          = "ASSIGNMENT",          "Assignment"
        SYSTEM              = "SYSTEM",              "System Notification"

    class Status(models.TextChoices):
        UNREAD   = "UNREAD",   "Unread"
        READ     = "READ",     "Read"
        ARCHIVED = "ARCHIVED", "Archived"

    recipient         = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title             = models.CharField(max_length=200)
    message           = models.TextField()
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices)
    contract          = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    status      = models.CharField(max_length=10, choices=Status.choices, default=Status.UNREAD)
    created_at  = models.DateTimeField(auto_now_add=True)
    read_at     = models.DateTimeField(null=True, blank=True)   # set when marked READ
    archived_at = models.DateTimeField(null=True, blank=True)   # set when ARCHIVED

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.recipient.username} — {self.title}"

    def mark_read(self):
        if self.status == self.Status.UNREAD:
            self.status  = self.Status.READ
            self.read_at = timezone.now()
            self.save(update_fields=["status", "read_at"])
