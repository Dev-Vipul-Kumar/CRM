"""
Utility functions for creating notifications.
"""
from .models import Notification


def _create(recipient, title, message, notification_type, contract=None):
    Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
        contract=contract,
    )


def notify_contract_update(contract, actor):
    """Notify assigned users when a contract is updated."""
    recipients = set()
    for assignment in contract.assignments.select_related("user"):
        recipients.add(assignment.user)
    if contract.owner and contract.owner != actor:
        recipients.add(contract.owner)

    for user in recipients:
        if user != actor:
            _create(
                recipient=user,
                title=f"Contract Updated: {contract.contract_number}",
                message=f"Contract '{contract.title}' has been updated by {actor.full_name}.",
                notification_type=Notification.NotificationType.CONTRACT_UPDATED,
                contract=contract,
            )


def notify_approval_required(contract, actor):
    """Notify managers/admins that a contract needs approval."""
    from accounts.models import User
    managers = User.objects.filter(
        role__in=[User.Role.ADMIN, User.Role.MANAGER],
        status=User.Status.ACTIVE,
    )
    for manager in managers:
        if manager != actor:
            _create(
                recipient=manager,
                title=f"Approval Required: {contract.contract_number}",
                message=f"Contract '{contract.title}' has been submitted for approval.",
                notification_type=Notification.NotificationType.APPROVAL_REQUIRED,
                contract=contract,
            )


def notify_contract_approved(contract, actor):
    if contract.owner and contract.owner != actor:
        _create(
            recipient=contract.owner,
            title=f"Contract Approved: {contract.contract_number}",
            message=f"Contract '{contract.title}' has been approved by {actor.full_name}.",
            notification_type=Notification.NotificationType.CONTRACT_APPROVED,
            contract=contract,
        )


def notify_contract_rejected(contract, actor):
    if contract.owner and contract.owner != actor:
        _create(
            recipient=contract.owner,
            title=f"Contract Rejected: {contract.contract_number}",
            message=f"Contract '{contract.title}' has been rejected by {actor.full_name}.",
            notification_type=Notification.NotificationType.CONTRACT_REJECTED,
            contract=contract,
        )


def notify_signature_required(contract, signer, actor):
    _create(
        recipient=signer,
        title=f"Signature Required: {contract.contract_number}",
        message=f"Your signature is required on contract '{contract.title}'.",
        notification_type=Notification.NotificationType.SIGNATURE_REQUIRED,
        contract=contract,
    )


def notify_expiry(contract, days_remaining):
    """Notify owner and assigned users about upcoming expiry."""
    recipients = set()
    if contract.owner:
        recipients.add(contract.owner)
    for assignment in contract.assignments.select_related("user"):
        recipients.add(assignment.user)

    if days_remaining <= 0:
        title   = f"Contract Expired: {contract.contract_number}"
        message = f"Contract '{contract.title}' has expired."
        ntype   = Notification.NotificationType.CONTRACT_EXPIRY
    else:
        title   = f"Contract Expiring Soon: {contract.contract_number}"
        message = f"Contract '{contract.title}' expires in {days_remaining} day(s)."
        ntype   = Notification.NotificationType.RENEWAL_REMINDER

    for user in recipients:
        _create(recipient=user, title=title, message=message,
                notification_type=ntype, contract=contract)
