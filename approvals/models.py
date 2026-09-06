from django.db import models
from django.conf import settings


class Approval(models.Model):

    class Action(models.TextChoices):
        SUBMITTED        = "SUBMITTED",        "Submitted for Review"
        APPROVED         = "APPROVED",         "Approved"
        REJECTED         = "REJECTED",         "Rejected"
        CHANGES_REQUESTED = "CHANGES_REQUESTED", "Changes Requested"

    contract  = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.CASCADE,
        related_name="approvals",
    )
    reviewer  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="approvals_given",
    )
    action    = models.CharField(max_length=25, choices=Action.choices)
    comment   = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.contract.contract_number} — {self.action} by {self.reviewer}"
