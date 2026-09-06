"""
Tests for the audit trail.
"""

import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from contracts.models import Contract, ContractVersion
from audit.models import AuditLog, log_action


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_user(username, role=User.Role.ADMIN):
    u = User(username=username, role=role, status=User.Status.ACTIVE)
    u.set_password("Pass1234!")
    u.save()
    return u


def make_contract(owner):
    today = timezone.now().date()
    c = Contract(
        title="Audit Test",
        party_name="Vendor",
        start_date=today,
        end_date=today + datetime.timedelta(days=180),
        status=Contract.Status.ACTIVE,
        priority=Contract.Priority.LOW,
        owner=owner,
        created_by=owner,
    )
    c.save()
    ContractVersion.objects.create(
        contract=c, version_number=1, created_by=owner,
        change_summary="Initial", is_current=True,
    )
    return c


# ── AuditLog model tests ───────────────────────────────────────────────────────

class AuditLogModelTests(TestCase):

    def setUp(self):
        self.admin = make_user("audit_admin")

    def test_log_action_creates_record(self):
        from django.test import RequestFactory
        rf      = RequestFactory()
        request = rf.get("/")
        request.user = self.admin
        request.META["REMOTE_ADDR"] = "127.0.0.1"

        log_action(request, AuditLog.Action.CREATE, "contracts",
                   "Created test contract", "Contract", 1)

        log = AuditLog.objects.filter(action=AuditLog.Action.CREATE).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.user, self.admin)
        self.assertEqual(log.module, "contracts")
        self.assertEqual(log.ip_address, "127.0.0.1")

    def test_audit_ordering_newest_first(self):
        from django.test import RequestFactory
        rf      = RequestFactory()
        request = rf.get("/")
        request.user = self.admin
        request.META["REMOTE_ADDR"] = "127.0.0.1"

        log_action(request, AuditLog.Action.LOGIN,  "accounts", "Login 1")
        log_action(request, AuditLog.Action.LOGOUT, "accounts", "Logout 1")

        logs = list(AuditLog.objects.all())
        self.assertEqual(logs[0].action, AuditLog.Action.LOGOUT)


# ── Audit views ────────────────────────────────────────────────────────────────

class AuditViewTests(TestCase):

    def setUp(self):
        self.admin    = make_user("audit_admin2")
        self.manager  = make_user("audit_mgr", role=User.Role.MANAGER)
        self.employee = make_user("audit_emp", role=User.Role.EMPLOYEE)
        self.client   = Client()

    def test_admin_can_view_audit_list(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("audit:audit_list"))
        self.assertEqual(response.status_code, 200)

    def test_manager_cannot_view_audit_list(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("audit:audit_list"))
        self.assertRedirects(response, reverse("dashboard:index"))

    def test_employee_cannot_view_audit_list(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse("audit:audit_list"))
        self.assertRedirects(response, reverse("dashboard:index"))

    def test_audit_list_search_filter(self):
        self.client.force_login(self.admin)
        AuditLog.objects.create(
            user=self.admin,
            action=AuditLog.Action.CREATE,
            module="contracts",
            description="Created CTR-2026-0001",
        )
        response = self.client.get(
            reverse("audit:audit_list") + "?search=CTR-2026-0001"
        )
        self.assertContains(response, "CTR-2026-0001")

    def test_contract_activity_timeline_for_assigned_user(self):
        contract = make_contract(self.manager)
        from contracts.models import ContractAssignment
        ContractAssignment.objects.create(
            contract=contract, user=self.employee, assigned_by=self.manager
        )
        self.client.force_login(self.employee)
        response = self.client.get(
            reverse("audit:contract_activity", args=[contract.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_contract_activity_blocked_for_unassigned(self):
        contract = make_contract(self.manager)
        self.client.force_login(self.employee)
        response = self.client.get(
            reverse("audit:contract_activity", args=[contract.pk])
        )
        self.assertEqual(response.status_code, 403)
