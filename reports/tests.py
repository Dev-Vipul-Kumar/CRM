"""
Tests for reports and CSV export.
"""

import csv
import io
import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from contracts.models import Contract, ContractVersion


def make_user(username, role=User.Role.MANAGER):
    u = User(username=username, role=role, status=User.Status.ACTIVE)
    u.set_password("Pass1234!")
    u.save()
    return u


def make_contract(owner, status=Contract.Status.ACTIVE, title="Report Contract"):
    today = timezone.now().date()
    c = Contract(
        title=title,
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


class ReportViewTests(TestCase):

    def setUp(self):
        self.admin   = make_user("rpt_admin", role=User.Role.ADMIN)
        self.manager = make_user("rpt_mgr")
        self.employee = make_user("rpt_emp", role=User.Role.EMPLOYEE)
        self.client  = Client()

    def test_reports_page_loads_for_admin(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("reports:reports_index"))
        self.assertEqual(response.status_code, 200)

    def test_reports_page_loads_for_manager(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("reports:reports_index"))
        self.assertEqual(response.status_code, 200)

    def test_reports_blocked_for_employee(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse("reports:reports_index"))
        self.assertRedirects(response, reverse("dashboard:index"))

    def test_csv_export_returns_csv(self):
        self.client.force_login(self.admin)
        make_contract(self.admin, title="Export Contract")
        response = self.client.get(reverse("reports:export_csv"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

    def test_csv_contains_contract_data(self):
        self.client.force_login(self.admin)
        c = make_contract(self.admin, title="CSV Test Contract")
        response = self.client.get(reverse("reports:export_csv"))
        content = response.content.decode("utf-8")
        self.assertIn("CSV Test Contract", content)
        self.assertIn(c.contract_number, content)

    def test_csv_has_header_row(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("reports:export_csv"))
        reader  = csv.reader(io.StringIO(response.content.decode("utf-8")))
        headers = next(reader)
        self.assertIn("Contract Number", headers)
        self.assertIn("Title", headers)
        self.assertIn("Status", headers)

    def test_status_counts_in_context(self):
        self.client.force_login(self.admin)
        make_contract(self.admin, status=Contract.Status.ACTIVE, title="Active 1")
        make_contract(self.admin, status=Contract.Status.EXPIRED, title="Expired 1")
        response = self.client.get(reverse("reports:reports_index"))
        ctx = response.context
        self.assertIn("status_counts", ctx)
