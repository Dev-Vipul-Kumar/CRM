"""
Tests for the digital signature workflow.
"""

import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from contracts.models import Contract, ContractVersion, ContractAssignment
from signatures.models import Signature


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_user(username, role=User.Role.MANAGER):
    u = User(username=username, role=role, status=User.Status.ACTIVE)
    u.set_password("Pass1234!")
    u.save()
    return u


def make_approved_contract(owner):
    today = timezone.now().date()
    c = Contract(
        title="Sig Test Contract",
        party_name="Vendor",
        start_date=today,
        end_date=today + datetime.timedelta(days=180),
        status=Contract.Status.APPROVED,
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


def make_pending_signature(contract, signer, requester):
    return Signature.objects.create(
        contract=contract,
        signer=signer,
        requested_by=requester,
        contract_version=contract.current_version,
        status=Signature.Status.PENDING,
    )


# ── Signature request tests ────────────────────────────────────────────────────

class SignatureRequestTests(TestCase):

    def setUp(self):
        self.manager  = make_user("mgr")
        self.employee = make_user("emp", role=User.Role.EMPLOYEE)
        self.contract = make_approved_contract(self.manager)
        ContractAssignment.objects.create(
            contract=self.contract, user=self.employee, assigned_by=self.manager
        )
        self.client = Client()
        self.client.force_login(self.manager)

    def test_request_signature_page_loads(self):
        response = self.client.get(
            reverse("signatures:request_signature", args=[self.contract.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_request_signature_creates_record(self):
        self.client.post(
            reverse("signatures:request_signature", args=[self.contract.pk]),
            {"signers": [self.employee.pk]},
        )
        self.assertTrue(
            Signature.objects.filter(
                contract=self.contract,
                signer=self.employee,
                status=Signature.Status.PENDING,
            ).exists()
        )

    def test_request_signature_sets_contract_pending(self):
        self.client.post(
            reverse("signatures:request_signature", args=[self.contract.pk]),
            {"signers": [self.employee.pk]},
        )
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, Contract.Status.PENDING_SIGNATURE)

    def test_employee_cannot_request_signature(self):
        self.client.force_login(self.employee)
        response = self.client.post(
            reverse("signatures:request_signature", args=[self.contract.pk]),
            {"signers": [self.employee.pk]},
        )
        self.assertRedirects(response, reverse("dashboard:index"))

    def test_cannot_request_signature_for_draft(self):
        from contracts.models import Contract as C
        self.contract.status = C.Status.DRAFT
        self.contract.save()
        response = self.client.post(
            reverse("signatures:request_signature", args=[self.contract.pk]),
            {"signers": [self.employee.pk]},
        )
        self.contract.refresh_from_db()
        self.assertNotEqual(self.contract.status, Contract.Status.PENDING_SIGNATURE)


# ── Signing tests ──────────────────────────────────────────────────────────────

class SignContractTests(TestCase):

    def setUp(self):
        self.manager  = make_user("mgr")
        self.employee = make_user("emp", role=User.Role.EMPLOYEE)
        self.contract = make_approved_contract(self.manager)
        self.sig      = make_pending_signature(self.contract, self.employee, self.manager)
        self.client   = Client()

    def test_sign_page_loads_for_signer(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse("signatures:sign_contract", args=[self.sig.pk]))
        self.assertEqual(response.status_code, 200)

    def test_non_signer_cannot_access_sign_page(self):
        other = make_user("other_emp", role=User.Role.EMPLOYEE)
        self.client.force_login(other)
        response = self.client.post(
            reverse("signatures:sign_contract", args=[self.sig.pk]),
            {"action": "sign", "signature_data": "data:image/png;base64,abc"},
        )
        # Redirected away with error
        self.assertRedirects(response, reverse("signatures:signature_list"))

    def test_sign_contract_marks_signed(self):
        self.client.force_login(self.employee)
        self.client.post(
            reverse("signatures:sign_contract", args=[self.sig.pk]),
            {"action": "sign", "signature_data": "data:image/png;base64,abc123"},
        )
        self.sig.refresh_from_db()
        self.assertEqual(self.sig.status, Signature.Status.SIGNED)

    def test_signed_at_timestamp_set(self):
        self.client.force_login(self.employee)
        self.client.post(
            reverse("signatures:sign_contract", args=[self.sig.pk]),
            {"action": "sign", "signature_data": "data:image/png;base64,abc123"},
        )
        self.sig.refresh_from_db()
        self.assertIsNotNone(self.sig.signed_at)

    def test_all_signed_activates_contract(self):
        self.client.force_login(self.employee)
        self.client.post(
            reverse("signatures:sign_contract", args=[self.sig.pk]),
            {"action": "sign", "signature_data": "data:image/png;base64,abc"},
        )
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, Contract.Status.ACTIVE)

    def test_reject_signature(self):
        self.client.force_login(self.employee)
        self.client.post(
            reverse("signatures:sign_contract", args=[self.sig.pk]),
            {"action": "reject", "rejection_reason": "Terms unclear"},
        )
        self.sig.refresh_from_db()
        self.assertEqual(self.sig.status, Signature.Status.REJECTED)
        self.assertEqual(self.sig.rejection_reason, "Terms unclear")

    def test_already_signed_cannot_be_signed_again(self):
        self.sig.status = Signature.Status.SIGNED
        self.sig.save()
        self.client.force_login(self.employee)
        response = self.client.post(
            reverse("signatures:sign_contract", args=[self.sig.pk]),
            {"action": "sign", "signature_data": "data:image/png;base64,xyz"},
        )
        self.assertRedirects(response, reverse("signatures:signature_list"))

    def test_signature_list_loads(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse("signatures:signature_list"))
        self.assertEqual(response.status_code, 200)
