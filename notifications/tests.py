"""
Tests for notifications and renewal alerts.
"""

import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from contracts.models import Contract, ContractVersion, ContractAssignment
from notifications.models import Notification
from notifications.utils import (
    notify_contract_update,
    notify_approval_required,
    notify_contract_approved,
    notify_contract_rejected,
    notify_signature_required,
    notify_expiry,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_user(username, role=User.Role.MANAGER):
    u = User(username=username, role=role, status=User.Status.ACTIVE)
    u.set_password("Pass1234!")
    u.save()
    return u


def make_contract(owner, days_until_expiry=90):
    today = timezone.now().date()
    c = Contract(
        title="Notif Test Contract",
        party_name="Vendor",
        start_date=today,
        end_date=today + datetime.timedelta(days=days_until_expiry),
        status=Contract.Status.ACTIVE,
        priority=Contract.Priority.MEDIUM,
        owner=owner,
        created_by=owner,
    )
    c.save()
    ContractVersion.objects.create(
        contract=c, version_number=1, created_by=owner,
        change_summary="Initial", is_current=True,
    )
    return c


# ── Notification utility tests ─────────────────────────────────────────────────

class NotificationUtilityTests(TestCase):

    def setUp(self):
        self.manager  = make_user("mgr")
        self.employee = make_user("emp", role=User.Role.EMPLOYEE)
        self.contract = make_contract(self.manager)
        ContractAssignment.objects.create(
            contract=self.contract, user=self.employee, assigned_by=self.manager
        )

    def test_notify_contract_update_sends_to_assigned_users(self):
        notify_contract_update(self.contract, actor=self.manager)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.employee,
                notification_type=Notification.NotificationType.CONTRACT_UPDATED,
            ).exists()
        )

    def test_notify_contract_update_does_not_send_to_actor(self):
        notify_contract_update(self.contract, actor=self.manager)
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.manager,
                notification_type=Notification.NotificationType.CONTRACT_UPDATED,
            ).exists()
        )

    def test_notify_approval_required(self):
        manager2 = make_user("mgr2")
        notify_approval_required(self.contract, actor=self.employee)
        self.assertTrue(
            Notification.objects.filter(
                notification_type=Notification.NotificationType.APPROVAL_REQUIRED,
            ).exists()
        )

    def test_notify_contract_approved(self):
        notify_contract_approved(self.contract, actor=self.employee)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.manager,
                notification_type=Notification.NotificationType.CONTRACT_APPROVED,
            ).exists()
        )

    def test_notify_contract_rejected(self):
        notify_contract_rejected(self.contract, actor=self.employee)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.manager,
                notification_type=Notification.NotificationType.CONTRACT_REJECTED,
            ).exists()
        )

    def test_notify_signature_required(self):
        notify_signature_required(self.contract, self.employee, actor=self.manager)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.employee,
                notification_type=Notification.NotificationType.SIGNATURE_REQUIRED,
            ).exists()
        )

    def test_notify_expiry_soon(self):
        notify_expiry(self.contract, days_remaining=25)
        self.assertTrue(
            Notification.objects.filter(
                notification_type=Notification.NotificationType.RENEWAL_REMINDER,
            ).exists()
        )

    def test_notify_expiry_expired(self):
        notify_expiry(self.contract, days_remaining=-1)
        self.assertTrue(
            Notification.objects.filter(
                notification_type=Notification.NotificationType.CONTRACT_EXPIRY,
            ).exists()
        )


# ── Renewal management command tests ──────────────────────────────────────────

class RenewalCommandTests(TestCase):

    def setUp(self):
        self.manager = make_user("mgr_renew")

    def test_check_renewals_marks_expired(self):
        c = make_contract(self.manager, days_until_expiry=-5)
        c.status = Contract.Status.ACTIVE
        c.save()

        from django.core.management import call_command
        call_command("check_renewals", verbosity=0)

        c.refresh_from_db()
        self.assertEqual(c.status, Contract.Status.EXPIRED)

    def test_check_renewals_marks_expiring_soon(self):
        c = make_contract(self.manager, days_until_expiry=5)
        c.status = Contract.Status.ACTIVE
        c.save()

        from django.core.management import call_command
        call_command("check_renewals", verbosity=0)

        c.refresh_from_db()
        self.assertEqual(c.status, Contract.Status.EXPIRING_SOON)

    def test_check_renewals_generates_notifications(self):
        c = make_contract(self.manager, days_until_expiry=3)
        c.status = Contract.Status.ACTIVE
        c.save()

        from django.core.management import call_command
        call_command("check_renewals", verbosity=0)

        self.assertTrue(
            Notification.objects.filter(contract=c).exists()
        )

    def test_check_renewals_does_not_touch_healthy_contracts(self):
        c = make_contract(self.manager, days_until_expiry=200)
        c.status = Contract.Status.ACTIVE
        c.save()

        from django.core.management import call_command
        call_command("check_renewals", verbosity=0)

        c.refresh_from_db()
        self.assertEqual(c.status, Contract.Status.ACTIVE)


# ── Notification views ─────────────────────────────────────────────────────────

class NotificationViewTests(TestCase):

    def setUp(self):
        self.user   = make_user("notif_user")
        self.client = Client()
        self.client.force_login(self.user)

    def test_notification_list_loads(self):
        response = self.client.get(reverse("notifications:notification_list"))
        self.assertEqual(response.status_code, 200)

    def test_mark_notification_read(self):
        contract = make_contract(self.user)
        notif = Notification.objects.create(
            recipient=self.user,
            title="Test",
            message="Test message",
            notification_type=Notification.NotificationType.SYSTEM,
            contract=contract,
            status=Notification.Status.UNREAD,
        )
        self.client.get(reverse("notifications:mark_read", args=[notif.pk]))
        notif.refresh_from_db()
        self.assertEqual(notif.status, Notification.Status.READ)

    def test_mark_all_read(self):
        contract = make_contract(self.user)
        for i in range(3):
            Notification.objects.create(
                recipient=self.user,
                title=f"Notif {i}",
                message="msg",
                notification_type=Notification.NotificationType.SYSTEM,
                contract=contract,
                status=Notification.Status.UNREAD,
            )
        self.client.post(reverse("notifications:mark_all_read"))
        unread = Notification.objects.filter(
            recipient=self.user,
            status=Notification.Status.UNREAD,
        ).count()
        self.assertEqual(unread, 0)

    def test_cannot_mark_other_users_notification(self):
        other = make_user("other_user")
        contract = make_contract(other)
        notif = Notification.objects.create(
            recipient=other,
            title="Other",
            message="msg",
            notification_type=Notification.NotificationType.SYSTEM,
            contract=contract,
            status=Notification.Status.UNREAD,
        )
        response = self.client.get(reverse("notifications:mark_read", args=[notif.pk]))
        self.assertEqual(response.status_code, 404)
        notif.refresh_from_db()
        self.assertEqual(notif.status, Notification.Status.UNREAD)

    def test_archive_notification(self):
        contract = make_contract(self.user)
        notif = Notification.objects.create(
            recipient=self.user,
            title="Archive Me",
            message="msg",
            notification_type=Notification.NotificationType.SYSTEM,
            contract=contract,
        )
        self.client.post(reverse("notifications:archive_notification", args=[notif.pk]))
        notif.refresh_from_db()
        self.assertEqual(notif.status, Notification.Status.ARCHIVED)
