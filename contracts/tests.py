"""
Tests for contract management, version control, assignment, and search/filter.
"""

import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import User, Department
from contracts.models import (
    Contract, ContractVersion, ContractCategory, ContractAssignment
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_user(username, role=User.Role.MANAGER, **kw):
    u = User(username=username, role=role, status=User.Status.ACTIVE, **kw)
    u.set_password("Pass1234!")
    u.save()
    return u


def make_contract(owner, **kwargs):
    today = timezone.now().date()
    defaults = dict(
        title="Test Contract",
        party_name="Test Vendor",
        start_date=today,
        end_date=today + datetime.timedelta(days=365),
        status=Contract.Status.DRAFT,
        priority=Contract.Priority.MEDIUM,
        created_by=owner,
        owner=owner,
    )
    defaults.update(kwargs)
    contract = Contract(**defaults)
    contract.save()
    ContractVersion.objects.create(
        contract=contract,
        version_number=1,
        created_by=owner,
        change_summary="Initial",
        is_current=True,
    )
    return contract


# ── Contract number generation ─────────────────────────────────────────────────

class ContractNumberTests(TestCase):

    def setUp(self):
        self.manager = make_user("mgr", role=User.Role.MANAGER)

    def test_contract_number_is_generated(self):
        c = make_contract(self.manager)
        self.assertTrue(c.contract_number.startswith("CTR-"))

    def test_contract_numbers_are_sequential(self):
        c1 = make_contract(self.manager, title="C1")
        c2 = make_contract(self.manager, title="C2")
        n1 = int(c1.contract_number.split("-")[-1])
        n2 = int(c2.contract_number.split("-")[-1])
        self.assertEqual(n2, n1 + 1)

    def test_contract_number_includes_year(self):
        c = make_contract(self.manager)
        year = str(timezone.now().year)
        self.assertIn(year, c.contract_number)

    def test_contract_number_unchanged_after_edit(self):
        c = make_contract(self.manager)
        original_number = c.contract_number
        c.title = "Updated Title"
        c.save()
        self.assertEqual(c.contract_number, original_number)


# ── Contract CRUD views ────────────────────────────────────────────────────────

class ContractCRUDTests(TestCase):

    def setUp(self):
        self.manager  = make_user("mgr")
        self.admin    = make_user("adm", role=User.Role.ADMIN)
        self.employee = make_user("emp", role=User.Role.EMPLOYEE)
        self.client   = Client()

    def test_contract_list_accessible_for_manager(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("contracts:contract_list"))
        self.assertEqual(response.status_code, 200)

    def test_contract_create_page_loads_for_manager(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("contracts:contract_create"))
        self.assertEqual(response.status_code, 200)

    def test_contract_create_blocked_for_employee(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse("contracts:contract_create"))
        self.assertRedirects(response, reverse("dashboard:index"))

    def test_contract_create_post(self):
        self.client.force_login(self.manager)
        today = timezone.now().date()
        response = self.client.post(reverse("contracts:contract_create"), {
            "title":          "New Contract",
            "party_name":     "Vendor Co",
            "start_date":     today.isoformat(),
            "end_date":       (today + datetime.timedelta(days=90)).isoformat(),
            "priority":       "MEDIUM",
            "change_summary": "Initial version",
        })
        self.assertTrue(Contract.objects.filter(title="New Contract").exists())
        contract = Contract.objects.get(title="New Contract")
        self.assertEqual(contract.versions.count(), 1)

    def test_contract_detail_visible_to_owner(self):
        self.client.force_login(self.manager)
        c = make_contract(self.manager)
        response = self.client.get(reverse("contracts:contract_detail", args=[c.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, c.contract_number)

    def test_contract_detail_blocked_for_unassigned_employee(self):
        self.client.force_login(self.employee)
        c = make_contract(self.manager)
        response = self.client.get(reverse("contracts:contract_detail", args=[c.pk]))
        self.assertEqual(response.status_code, 403)

    def test_employee_can_view_assigned_contract(self):
        self.client.force_login(self.employee)
        c = make_contract(self.manager)
        ContractAssignment.objects.create(contract=c, user=self.employee, assigned_by=self.manager)
        response = self.client.get(reverse("contracts:contract_detail", args=[c.pk]))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_view_any_contract(self):
        self.client.force_login(self.admin)
        c = make_contract(self.manager)
        response = self.client.get(reverse("contracts:contract_detail", args=[c.pk]))
        self.assertEqual(response.status_code, 200)

    def test_contract_edit(self):
        self.client.force_login(self.manager)
        c = make_contract(self.manager)
        today = timezone.now().date()
        self.client.post(reverse("contracts:contract_edit", args=[c.pk]), {
            "title":      "Edited Title",
            "party_name": c.party_name,
            "start_date": c.start_date.isoformat(),
            "end_date":   c.end_date.isoformat(),
            "priority":   c.priority,
        })
        c.refresh_from_db()
        self.assertEqual(c.title, "Edited Title")

    def test_contract_archive(self):
        self.client.force_login(self.admin)
        c = make_contract(self.admin)
        self.client.post(reverse("contracts:contract_archive", args=[c.pk]))
        c.refresh_from_db()
        self.assertEqual(c.status, Contract.Status.ARCHIVED)


# ── Contract properties ────────────────────────────────────────────────────────

class ContractPropertyTests(TestCase):

    def setUp(self):
        self.manager = make_user("mgr")

    def test_days_until_expiry_positive(self):
        c = make_contract(self.manager,
                          end_date=timezone.now().date() + datetime.timedelta(days=45))
        self.assertEqual(c.days_until_expiry, 45)

    def test_days_until_expiry_negative_when_expired(self):
        c = make_contract(self.manager,
                          end_date=timezone.now().date() - datetime.timedelta(days=5))
        self.assertEqual(c.days_until_expiry, -5)

    def test_expiry_urgency_critical(self):
        c = make_contract(self.manager,
                          end_date=timezone.now().date() + datetime.timedelta(days=5))
        self.assertEqual(c.expiry_urgency, "critical")

    def test_expiry_urgency_warning(self):
        c = make_contract(self.manager,
                          end_date=timezone.now().date() + datetime.timedelta(days=25))
        self.assertEqual(c.expiry_urgency, "warning")

    def test_expiry_urgency_normal(self):
        c = make_contract(self.manager,
                          end_date=timezone.now().date() + datetime.timedelta(days=90))
        self.assertEqual(c.expiry_urgency, "normal")

    def test_is_expired(self):
        c = make_contract(self.manager,
                          end_date=timezone.now().date() - datetime.timedelta(days=1))
        self.assertTrue(c.is_expired)


# ── Version control tests ──────────────────────────────────────────────────────

class VersionControlTests(TestCase):

    def setUp(self):
        self.manager = make_user("mgr")
        self.contract = make_contract(self.manager)
        self.client = Client()
        self.client.force_login(self.manager)

    def test_initial_version_created(self):
        self.assertEqual(self.contract.versions.count(), 1)
        self.assertEqual(self.contract.versions.first().version_number, 1)

    def test_current_version_flag(self):
        v = self.contract.versions.first()
        self.assertTrue(v.is_current)

    def test_upload_new_version(self):
        doc = SimpleUploadedFile("test.pdf", b"PDF content", content_type="application/pdf")
        self.client.post(
            reverse("contracts:contract_upload_version", args=[self.contract.pk]),
            {"change_summary": "Second upload", "document": doc},
        )
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.versions.count(), 2)

    def test_new_version_becomes_current(self):
        doc = SimpleUploadedFile("test2.pdf", b"PDF content", content_type="application/pdf")
        self.client.post(
            reverse("contracts:contract_upload_version", args=[self.contract.pk]),
            {"change_summary": "V2", "document": doc},
        )
        current = self.contract.versions.filter(is_current=True)
        self.assertEqual(current.count(), 1)
        self.assertEqual(current.first().version_number, 2)

    def test_old_version_not_deleted(self):
        doc = SimpleUploadedFile("test3.pdf", b"data", content_type="application/pdf")
        self.client.post(
            reverse("contracts:contract_upload_version", args=[self.contract.pk]),
            {"change_summary": "V2", "document": doc},
        )
        self.assertEqual(self.contract.versions.count(), 2)

    def test_version_history_page_loads(self):
        response = self.client.get(reverse("contracts:contract_versions", args=[self.contract.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Version History")


# ── Search and filter tests ────────────────────────────────────────────────────

class ContractSearchFilterTests(TestCase):

    def setUp(self):
        self.admin = make_user("adm", role=User.Role.ADMIN)
        make_contract(self.admin, title="Aviation Training Agreement",
                      status=Contract.Status.ACTIVE)
        make_contract(self.admin, title="IT Maintenance Contract",
                      status=Contract.Status.EXPIRED)
        self.client = Client()
        self.client.force_login(self.admin)

    def test_search_by_title(self):
        response = self.client.get(reverse("contracts:contract_list") + "?search=Aviation")
        self.assertContains(response, "Aviation Training Agreement")
        self.assertNotContains(response, "IT Maintenance Contract")

    def test_search_case_insensitive(self):
        response = self.client.get(reverse("contracts:contract_list") + "?search=aviation")
        self.assertContains(response, "Aviation Training Agreement")

    def test_filter_by_status(self):
        response = self.client.get(
            reverse("contracts:contract_list") + "?status=EXPIRED"
        )
        self.assertContains(response, "IT Maintenance Contract")
        self.assertNotContains(response, "Aviation Training Agreement")

    def test_empty_search_returns_all(self):
        response = self.client.get(reverse("contracts:contract_list"))
        self.assertContains(response, "Aviation Training Agreement")
        self.assertContains(response, "IT Maintenance Contract")


# ── Assignment tests ───────────────────────────────────────────────────────────

class AssignmentTests(TestCase):

    def setUp(self):
        self.manager  = make_user("mgr")
        self.employee = make_user("emp", role=User.Role.EMPLOYEE)
        self.contract = make_contract(self.manager)
        self.client   = Client()
        self.client.force_login(self.manager)

    def test_assign_user_to_contract(self):
        self.client.post(
            reverse("contracts:contract_assign", args=[self.contract.pk]),
            {"users": [self.employee.pk], "notes": ""},
        )
        self.assertTrue(
            ContractAssignment.objects.filter(
                contract=self.contract, user=self.employee
            ).exists()
        )

    def test_remove_assignment(self):
        ContractAssignment.objects.create(
            contract=self.contract, user=self.employee, assigned_by=self.manager
        )
        # Post with empty users list to remove
        self.client.post(
            reverse("contracts:contract_assign", args=[self.contract.pk]),
            {"users": [], "notes": ""},
        )
        self.assertFalse(
            ContractAssignment.objects.filter(
                contract=self.contract, user=self.employee
            ).exists()
        )
