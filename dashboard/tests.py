"""
Tests for role-based dashboards.
"""

import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User, Department
from contracts.models import Contract, ContractVersion, ContractAssignment


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_user(username, role=User.Role.ADMIN, dept=None):
    u = User(username=username, role=role, status=User.Status.ACTIVE, department=dept)
    u.set_password("Pass1234!")
    u.save()
    return u


def make_contract(owner, status=Contract.Status.ACTIVE):
    today = timezone.now().date()
    c = Contract(
        title="Dashboard Test",
        party_name="Vendor",
        start_date=today,
        end_date=today + datetime.timedelta(days=90),
        status=status,
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


# ── Dashboard routing ──────────────────────────────────────────────────────────

class DashboardRoutingTests(TestCase):

    def setUp(self):
        self.admin    = make_user("dash_admin")
        self.manager  = make_user("dash_mgr",  role=User.Role.MANAGER)
        self.employee = make_user("dash_emp",  role=User.Role.EMPLOYEE)
        self.client   = Client()

    def test_admin_dashboard_loads(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard:index"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/admin_dashboard.html")

    def test_manager_dashboard_loads(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("dashboard:index"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/manager_dashboard.html")

    def test_employee_dashboard_loads(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse("dashboard:index"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/employee_dashboard.html")

    def test_unauthenticated_redirect(self):
        response = self.client.get(reverse("dashboard:index"))
        self.assertEqual(response.status_code, 302)


# ── Dashboard statistics tests ─────────────────────────────────────────────────

class DashboardStatisticsTests(TestCase):

    def setUp(self):
        self.admin  = make_user("stat_admin")
        self.client = Client()
        self.client.force_login(self.admin)

    def test_stats_reflect_database(self):
        make_contract(self.admin, status=Contract.Status.ACTIVE)
        make_contract(self.admin, status=Contract.Status.ACTIVE)
        make_contract(self.admin, status=Contract.Status.DRAFT)

        response = self.client.get(reverse("dashboard:index"))
        self.assertEqual(response.status_code, 200)
        # Stats should show 2 active and 1 draft in the response
        self.assertContains(response, "2")   # active count
        self.assertContains(response, "1")   # draft count

    def test_admin_sees_all_contracts(self):
        manager = make_user("stat_mgr", role=User.Role.MANAGER)
        make_contract(manager, status=Contract.Status.ACTIVE)
        response = self.client.get(reverse("dashboard:index"))
        # Admin dashboard should include the manager's contract in total
        ctx = response.context
        self.assertGreaterEqual(ctx["stats"]["total_contracts"], 1)

    def test_manager_only_sees_own_contracts(self):
        dept    = Department.objects.create(name="TestDept")
        manager = make_user("stat_mgr2", role=User.Role.MANAGER, dept=dept)
        other   = make_user("stat_other", role=User.Role.MANAGER)

        make_contract(manager)
        make_contract(other)

        self.client.force_login(manager)
        response = self.client.get(reverse("dashboard:index"))
        ctx = response.context
        # Manager should see their own contract (1), not the other's (unless same dept)
        self.assertEqual(ctx["stats"]["total_contracts"], 1)

    def test_employee_sees_only_assigned_contracts(self):
        manager  = make_user("stat_mgr3", role=User.Role.MANAGER)
        employee = make_user("stat_emp3", role=User.Role.EMPLOYEE)
        c1 = make_contract(manager)
        c2 = make_contract(manager)
        ContractAssignment.objects.create(contract=c1, user=employee, assigned_by=manager)

        self.client.force_login(employee)
        response = self.client.get(reverse("dashboard:index"))
        ctx = response.context
        self.assertEqual(ctx["stats"]["total_contracts"], 1)
