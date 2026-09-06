"""
Management command: check_renewals

Run daily (cron / Windows Task Scheduler) to:
  - Mark expiring/expired contracts
  - Send renewal reminders (with deduplication — one per threshold per contract per day)
  - Write AuditLog entries for automated status transitions

Usage:
    python manage.py check_renewals
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings

from contracts.models import Contract
from notifications.models import Notification
from notifications.utils import notify_expiry
from audit.models import AuditLog


class Command(BaseCommand):
    help = "Check contract expiry dates and send renewal reminders"

    def handle(self, *args, **options):
        today      = timezone.now().date()
        thresholds = settings.RENEWAL_THRESHOLDS

        contracts = Contract.objects.filter(
            status__in=[
                Contract.Status.ACTIVE,
                Contract.Status.EXPIRING_SOON,
                Contract.Status.APPROVED,
            ]
        ).select_related("owner").prefetch_related("assignments__user")

        notified = 0
        expired  = 0
        skipped  = 0   # already notified today

        for contract in contracts:
            days = (contract.end_date - today).days

            if days < 0:
                # ── Mark expired ──────────────────────────────────────
                if contract.status != Contract.Status.EXPIRED:
                    contract.status = Contract.Status.EXPIRED
                    contract.save(update_fields=["status"])

                    # Audit log for automated status change
                    AuditLog.objects.create(
                        user=None,
                        action=AuditLog.Action.UPDATE,
                        module="contracts",
                        object_type="Contract",
                        object_id=str(contract.pk),
                        description=(
                            f"[AUTO] Contract {contract.contract_number} marked EXPIRED "
                            f"(end date: {contract.end_date})"
                        ),
                    )

                    # Notify — only if no EXPIRY notification exists for today
                    if not self._already_notified_today(contract, today):
                        notify_expiry(contract, days)
                        notified += 1
                    else:
                        skipped += 1
                    expired += 1

            elif days <= thresholds["critical"]:
                # ── Mark expiring soon ────────────────────────────────
                if contract.status != Contract.Status.EXPIRING_SOON:
                    contract.status = Contract.Status.EXPIRING_SOON
                    contract.save(update_fields=["status"])

                    AuditLog.objects.create(
                        user=None,
                        action=AuditLog.Action.UPDATE,
                        module="contracts",
                        object_type="Contract",
                        object_id=str(contract.pk),
                        description=(
                            f"[AUTO] Contract {contract.contract_number} marked EXPIRING_SOON "
                            f"({days} day(s) remaining)"
                        ),
                    )

                if not self._already_notified_today(contract, today):
                    notify_expiry(contract, days)
                    notified += 1
                else:
                    skipped += 1

            elif days <= thresholds["urgent"]:
                if not self._already_notified_today(contract, today):
                    notify_expiry(contract, days)
                    notified += 1
                else:
                    skipped += 1

            elif days <= thresholds["warning"]:
                if not self._already_notified_today(contract, today):
                    notify_expiry(contract, days)
                    notified += 1
                else:
                    skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"check_renewals complete: {notified} notification(s) sent, "
                f"{expired} contract(s) marked expired, "
                f"{skipped} already-notified skipped."
            )
        )

    @staticmethod
    def _already_notified_today(contract, today):
        """
        Returns True if a CONTRACT_EXPIRY or RENEWAL_REMINDER notification
        was already created for this contract today — prevents duplicate
        notifications on repeated daily runs.
        """
        return Notification.objects.filter(
            contract=contract,
            notification_type__in=[
                Notification.NotificationType.CONTRACT_EXPIRY,
                Notification.NotificationType.RENEWAL_REMINDER,
            ],
            created_at__date=today,
        ).exists()
