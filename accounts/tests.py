"""
Tests for authentication and user management.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from .models import User, Department


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_admin(**kwargs):
    defaults = dict(username="testadmin", password="Pass1234!", role=User.Role.ADMIN,
                    status=User.Status.ACTIVE, email="admin@test.com")
    defaults.update(kwargs)
    pw = defaults.pop("password")
    u = User(**defaults)
    u.set_password(pw)
    u.save()
    return u


def make_manager(**kwargs):
    defaults = dict(username="testmanager", password="Pass1234!", role=User.Role.MANAGER,
                    status=User.Status.ACTIVE, email="manager@test.com")
    defaults.update(kwargs)
    pw = defaults.pop("password")
    u = User(**defaults)
    u.set_password(pw)
    u.save()
    return u


def make_employee(**kwargs):
    defaults = dict(username="testemployee", password="Pass1234!", role=User.Role.EMPLOYEE,
                    status=User.Status.ACTIVE, email="employee@test.com")
    defaults.update(kwargs)
    pw = defaults.pop("password")
    u = User(**defaults)
    u.set_password(pw)
    u.save()
    return u


# ── Authentication tests ───────────────────────────────────────────────────────

class LoginTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = make_admin()

    def test_login_page_loads(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign In")

    def test_correct_credentials_redirect_to_dashboard(self):
        response = self.client.post(reverse("accounts:login"), {
            "username": "testadmin",
            "password": "Pass1234!",
        })
        self.assertRedirects(response, reverse("dashboard:index"))

    def test_wrong_password_shows_error(self):
        response = self.client.post(reverse("accounts:login"), {
            "username": "testadmin",
            "password": "wrongpassword",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password")

    def test_unknown_user_shows_error(self):
        response = self.client.post(reverse("accounts:login"), {
            "username": "nobody",
            "password": "Pass1234!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password")

    def test_inactive_user_cannot_login(self):
        inactive = make_employee(username="inactive_user", status=User.Status.INACTIVE)
        response = self.client.post(reverse("accounts:login"), {
            "username": "inactive_user",
            "password": "Pass1234!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "inactive")

    def test_suspended_user_cannot_login(self):
        suspended = make_employee(username="suspended_user", status=User.Status.SUSPENDED)
        response = self.client.post(reverse("accounts:login"), {
            "username": "suspended_user",
            "password": "Pass1234!",
        })
        self.assertEqual(response.status_code, 200)

    def test_logout_clears_session(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("accounts:login"))
        # Confirm session gone
        response = self.client.get(reverse("dashboard:index"))
        self.assertRedirects(response, "/login/?next=/dashboard/")

    def test_authenticated_user_skips_login_page(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("accounts:login"))
        self.assertRedirects(response, reverse("dashboard:index"))


# ── Role-based access tests ────────────────────────────────────────────────────

class RoleAccessTests(TestCase):

    def setUp(self):
        self.admin    = make_admin()
        self.manager  = make_manager()
        self.employee = make_employee()
        self.client   = Client()

    # Admin-only: user list
    def test_admin_can_access_user_list(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("accounts:user_list"))
        self.assertEqual(response.status_code, 200)

    def test_manager_cannot_access_user_list(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("accounts:user_list"))
        self.assertRedirects(response, reverse("dashboard:index"))

    def test_employee_cannot_access_user_list(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse("accounts:user_list"))
        self.assertRedirects(response, reverse("dashboard:index"))

    # Unauthenticated redirect
    def test_unauthenticated_user_redirected_from_dashboard(self):
        response = self.client.get(reverse("dashboard:index"))
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_user_redirected_from_contracts(self):
        response = self.client.get(reverse("contracts:contract_list"))
        self.assertEqual(response.status_code, 302)

    # Admin-only: audit log
    def test_admin_can_access_audit_log(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("audit:audit_list"))
        self.assertEqual(response.status_code, 200)

    def test_employee_cannot_access_audit_log(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse("audit:audit_list"))
        self.assertRedirects(response, reverse("dashboard:index"))


# ── User model tests ───────────────────────────────────────────────────────────

class UserModelTests(TestCase):

    def test_inactive_status_disables_login(self):
        u = make_employee(username="chkuser")
        self.assertTrue(u.is_active)
        u.status = User.Status.INACTIVE
        u.save()
        self.assertFalse(u.is_active)

    def test_full_name_falls_back_to_username(self):
        u = make_employee(username="noname")
        self.assertEqual(u.full_name, "noname")

    def test_full_name_returns_first_last(self):
        u = make_employee(username="withname", first_name="John", last_name="Doe")
        self.assertEqual(u.full_name, "John Doe")

    def test_role_properties(self):
        admin    = make_admin(username="a1")
        manager  = make_manager(username="m1")
        employee = make_employee(username="e1")
        self.assertTrue(admin.is_admin)
        self.assertFalse(admin.is_manager)
        self.assertTrue(manager.is_manager)
        self.assertTrue(employee.is_employee)


# ── User management CRUD tests ─────────────────────────────────────────────────

class UserManagementTests(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.client.force_login(self.admin)

    def test_create_user_form_renders(self):
        response = self.client.get(reverse("accounts:user_create"))
        self.assertEqual(response.status_code, 200)

    def test_create_user_post(self):
        response = self.client.post(reverse("accounts:user_create"), {
            "username":   "newuser",
            "email":      "new@test.com",
            "first_name": "New",
            "last_name":  "User",
            "role":       User.Role.EMPLOYEE,
            "status":     User.Status.ACTIVE,
            "phone":      "",
            "password1":  "StrongPass99!",
            "password2":  "StrongPass99!",
        })
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_toggle_user_status(self):
        target = make_employee(username="toggled")
        self.assertTrue(target.is_active)
        self.client.post(reverse("accounts:user_toggle_status", args=[target.pk]))
        target.refresh_from_db()
        self.assertFalse(target.is_active)


# ── Department tests ───────────────────────────────────────────────────────────

class DepartmentTests(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.client.force_login(self.admin)

    def test_create_department(self):
        self.client.post(reverse("accounts:department_create"), {
            "name":        "Engineering",
            "description": "Engineering dept",
        })
        self.assertTrue(Department.objects.filter(name="Engineering").exists())

    def test_delete_department(self):
        dept = Department.objects.create(name="Temp")
        self.client.post(reverse("accounts:department_delete", args=[dept.pk]))
        self.assertFalse(Department.objects.filter(pk=dept.pk).exists())
