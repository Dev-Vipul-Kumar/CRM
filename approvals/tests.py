"""
Tests for the contract approval workflow.
"""

import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from contracts.models import Contract, ContractVersion
from approvals.models import Approval


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_user(username, role=User.Role.MANAGER):
    u = User(username=username, role=role, status=User.Status.ACTIVE)
    u.set_password("Pass1234!")
    u.save()
    return u


def make_contract(owner, status=Contract.Status.DRAFT):
    today = timezone.now().date()
    c = Contract(
        title="Approval Test Contract",
        party_name="Vendor",
        start_date=today,
        end_date=today + datetime.timedelta(days=180),
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


# ── Submit for review tests ────────────────────────────────────────────────────

class SubmitForReviewTests(TestCase):

    def setUp(self):
        self.manager = make_user("mgr")
        self.client  = Client()
        self.client.force_login(self.manager)

    def test_submit_draft_contract(self):
        c = make_contract(self.manager, status=Contract.Status.DRAFT)
        self.client.post(
            reverse("approvals:submit_for_review", args=[c.pk]),
            {"comment": "Ready for review"},
        )
        c.refresh_from_db()
        self.assertEqual(c.status, Contract.Status.PENDING_APPROVAL)

    def test_submit_creates_approval_record(self):
        c = make_contract(self.manager)
        self.client.post(
            reverse("approvals:submit_for_review", args=[c.pk]),
            {"comment": "Submitting"},
        )
        self.assertTrue(
            Approval.objects.filter(
                contract=c, action=Approval.Action.SUBMITTED
            ).exists()
        )

    def test_cannot_submit_active_contract(self):
        c = make_contract(self.manager, status=Contract.Status.ACTIVE)
        self.client.post(
            reverse("approvals:submit_for_review", args=[c.pk]),
            {"comment": ""},
        )
        c.refresh_from_db()
        self.assertEqual(c.status, Contract.Status.ACTIVE)

    def test_employee_cannot_submit_for_review(self):
        employee = make_user("emp", role=User.Role.EMPLOYEE)
        c = make_contract(self.manager)
        self.client.force_login(employee)
        response = self.client.post(
            reverse("approvals:submit_for_review", args=[c.pk]),
            {"comment": ""},
        )
        self.assertRedirects(response, reverse("dashboard:index"))


# ── Approval action tests ─────────────────────────────────────────────────────

class ApprovalActionTests(TestCase):

    def setUp(self):
        self.manager = make_user("mgr")
        self.client  = Client()
        self.client.force_login(self.manager)

    def test_approve_contract(self):
        c = make_contract(self.manager, status=Contract.Status.PENDING_APPROVAL)
        self.client.post(
            reverse("approvals:approval_action", args=[c.pk]),
            {"action": Approval.Action.APPROVED, "comment": "All good"},
        )
        c.refresh_from_db()
        self.assertEqual(c.status, Contract.Status.APPROVED)

    def test_reject_contract(self):
        c = make_contract(self.manager, status=Contract.Status.PENDING_APPROVAL)
        self.client.post(
            reverse("approvals:approval_action", args=[c.pk]),
            {"action": Approval.Action.REJECTED, "comment": "Not acceptable"},
        )
        c.refresh_from_db()
        self.assertEqual(c.status, Contract.Status.REJECTED)

    def test_request_changes(self):
        c = make_contract(self.manager, status=Contract.Status.PENDING_APPROVAL)
        self.client.post(
            reverse("approvals:approval_action", args=[c.pk]),
            {"action": Approval.Action.CHANGES_REQUESTED, "comment": "Please update"},
        )
        c.refresh_from_db()
        self.assertEqual(c.status, Contract.Status.UNDER_REVIEW)

    def test_approval_record_created(self):
        c = make_contract(self.manager, status=Contract.Status.PENDING_APPROVAL)
        self.client.post(
            reverse("approvals:approval_action", args=[c.pk]),
            {"action": Approval.Action.APPROVED, "comment": ""},
        )
        self.assertTrue(
            Approval.objects.filter(
                contract=c, action=Approval.Action.APPROVED
            ).exists()
        )

    def test_cannot_approve_draft_contract(self):
        c = make_contract(self.manager, status=Contract.Status.DRAFT)
        self.client.post(
            reverse("approvals:approval_action", args=[c.pk]),
            {"action": Approval.Action.APPROVED, "comment": ""},
        )
        c.refresh_from_db()
        self.assertEqual(c.status, Contract.Status.DRAFT)

    def test_employee_cannot_approve(self):
        employee = make_user("emp2", role=User.Role.EMPLOYEE)
        c = make_contract(self.manager, status=Contract.Status.PENDING_APPROVAL)
        self.client.force_login(employee)
        response = self.client.post(
            reverse("approvals:approval_action", args=[c.pk]),
            {"action": Approval.Action.APPROVED, "comment": ""},
        )
        self.assertRedirects(response, reverse("dashboard:index"))
        c.refresh_from_db()
        self.assertNotEqual(c.status, Contract.Status.APPROVED)

    def test_approval_list_visible_to_manager(self):
        response = self.client.get(reverse("approvals:approval_list"))
        self.assertEqual(response.status_code, 200)


# ── Full workflow test ─────────────────────────────────────────────────────────

class ApprovalWorkflowTests(TestCase):
    """End-to-end: Draft → Pending Approval → Approved."""

    def test_full_approval_workflow(self):
        manager = make_user("wf_mgr")
        client  = Client()
        client.force_login(manager)

        c = make_contract(manager)
        self.assertEqual(c.status, Contract.Status.DRAFT)

        # Submit
        client.post(
            reverse("approvals:submit_for_review", args=[c.pk]),
            {"comment": "Ready"},
        )
        c.refresh_from_db()
        self.assertEqual(c.status, Contract.Status.PENDING_APPROVAL)

        # Approve
        client.post(
            reverse("approvals:approval_action", args=[c.pk]),
            {"action": Approval.Action.APPROVED, "comment": "Approved"},
        )
        c.refresh_from_db()
        self.assertEqual(c.status, Contract.Status.APPROVED)

        # Verify audit record count (submit + approve = 2)
        self.assertEqual(Approval.objects.filter(contract=c).count(), 2)
