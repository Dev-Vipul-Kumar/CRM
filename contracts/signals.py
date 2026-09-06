"""
contracts/signals.py

Django signals that run automatically on model saves.
These ensure important business state changes are always
persisted to the DB, regardless of which code path triggers them.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender="contracts.ContractVersion")
def version_created(sender, instance, created, **kwargs):
    """
    When a new version is created for a contract, record in audit.
    This fires for EVERY ContractVersion.save() so it works even if
    versions are created outside the normal views.
    """
    if not created:
        return
    try:
        from audit.models import AuditLog
        AuditLog.objects.create(
            user=instance.created_by,
            action=AuditLog.Action.CREATE,
            module="contracts",
            object_type="ContractVersion",
            object_id=str(instance.pk),
            description=(
                f"Version {instance.version_number} created for "
                f"{instance.contract.contract_number}"
            ),
        )
    except Exception:
        pass   # Never break the primary operation due to audit logging


@receiver(post_save, sender="contracts.ContractAssignment")
def assignment_created(sender, instance, created, **kwargs):
    """
    When a user is assigned to a contract, ensure a notification exists.
    Guards against assignments created outside the normal view
    (e.g. via admin, shell, or seed_data).
    """
    if not created:
        return
    try:
        from notifications.models import Notification
        already = Notification.objects.filter(
            recipient=instance.user,
            notification_type=Notification.NotificationType.ASSIGNMENT,
            contract=instance.contract,
        ).exists()
        if not already:
            Notification.objects.create(
                recipient=instance.user,
                title=f"Contract Assigned: {instance.contract.contract_number}",
                message=(
                    f"You have been assigned to contract "
                    f"'{instance.contract.title}'."
                ),
                notification_type=Notification.NotificationType.ASSIGNMENT,
                contract=instance.contract,
            )
    except Exception:
        pass
