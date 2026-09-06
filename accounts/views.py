from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator

from .models import User, Department
from .forms import LoginForm, UserCreateForm, UserEditForm, PasswordResetForm, DepartmentForm
from .decorators import admin_required
from audit.models import log_action, AuditLog


# ─── Landing page ─────────────────────────────────────────────────────────────

def landing(request):
    """Public landing page — no login required."""
    if request.user.is_authenticated:
        if request.user.role == request.user.Role.ADMIN:
            return redirect("accounts:admin_portal")
        return redirect("dashboard:index")
    return render(request, "landing.html")


# ─── Authentication ──────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:index")

    form = LoginForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]
        remember  = form.cleaned_data.get("remember_me", False)

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if not user.is_active:
                form.add_error(None, "Your account is inactive. Please contact an administrator.")
            else:
                login(request, user)
                # ── Audit: successful login ────────────────────────
                log_action(request, AuditLog.Action.LOGIN, "accounts",
                           f"User '{user.username}' logged in", "User", user.pk)
                if not remember:
                    request.session.set_expiry(0)
                else:
                    request.session.set_expiry(1209600)
                if user.role == User.Role.ADMIN:
                    return redirect("accounts:admin_portal")
                return redirect("dashboard:index")
        else:
            form.add_error(None, "Invalid username or password.")

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    # ── Audit: logout before session is cleared ────────────────
    if request.user.is_authenticated:
        log_action(request, AuditLog.Action.LOGOUT, "accounts",
                   f"User '{request.user.username}' logged out", "User", request.user.pk)
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("accounts:landing")


# ─── User Management (Admin only) ────────────────────────────────────────────

@login_required
@admin_required
def user_list(request):
    qs = User.objects.select_related("department").order_by("username")

    # Search
    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(username__icontains=search) | \
             qs.filter(first_name__icontains=search) | \
             qs.filter(last_name__icontains=search) | \
             qs.filter(email__icontains=search)

    # Filter
    role_filter   = request.GET.get("role", "")
    status_filter = request.GET.get("status", "")
    dept_filter   = request.GET.get("department", "")

    if role_filter:
        qs = qs.filter(role=role_filter)
    if status_filter:
        qs = qs.filter(status=status_filter)
    if dept_filter:
        qs = qs.filter(department_id=dept_filter)

    paginator = Paginator(qs, 15)
    page      = paginator.get_page(request.GET.get("page"))

    return render(request, "accounts/user_list.html", {
        "page_obj":    page,
        "search":      search,
        "role_filter": role_filter,
        "status_filter": status_filter,
        "dept_filter": dept_filter,
        "roles":       User.Role.choices,
        "statuses":    User.Status.choices,
        "departments": Department.objects.all(),
    })


@login_required
@admin_required
def user_create(request):
    form = UserCreateForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        log_action(request, AuditLog.Action.CREATE, "accounts",
                   f"Created user '{user.username}' (role: {user.get_role_display()})", "User", user.pk)
        messages.success(request, f"User '{user.username}' created successfully.")
        return redirect("accounts:user_list")

    return render(request, "accounts/user_form.html", {
        "form":  form,
        "title": "Create User",
        "action": "Create",
    })


@login_required
@admin_required
def user_detail(request, pk):
    user = get_object_or_404(User, pk=pk)
    return render(request, "accounts/user_detail.html", {"target_user": user})


@login_required
@admin_required
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    form = UserEditForm(request.POST or None, instance=user)

    if request.method == "POST" and form.is_valid():
        form.save()
        log_action(request, AuditLog.Action.UPDATE, "accounts",
                   f"Updated user '{user.username}'", "User", user.pk)
        messages.success(request, f"User '{user.username}' updated successfully.")
        return redirect("accounts:user_detail", pk=pk)

    return render(request, "accounts/user_form.html", {
        "form":        form,
        "title":       "Edit User",
        "action":      "Save Changes",
        "target_user": user,
    })


@login_required
@admin_required
def user_reset_password(request, pk):
    user = get_object_or_404(User, pk=pk)
    form = PasswordResetForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user.set_password(form.cleaned_data["new_password1"])
        user.save()
        log_action(request, AuditLog.Action.UPDATE, "accounts",
                   f"Reset password for user '{user.username}'", "User", user.pk)
        messages.success(request, f"Password for '{user.username}' has been reset.")
        return redirect("accounts:user_detail", pk=pk)

    return render(request, "accounts/password_reset.html", {
        "form":        form,
        "target_user": user,
    })


@login_required
@admin_required
def user_toggle_status(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        if user.status == User.Status.ACTIVE:
            user.status = User.Status.INACTIVE
            msg = f"User '{user.username}' has been deactivated."
        else:
            user.status = User.Status.ACTIVE
            msg = f"User '{user.username}' has been activated."
        user.save()
        log_action(request, AuditLog.Action.UPDATE, "accounts",
                   f"Toggled status of '{user.username}' → {user.status}", "User", user.pk)
        messages.success(request, msg)
    return redirect("accounts:user_detail", pk=pk)


# ─── Department Management (Admin only) ──────────────────────────────────────

@login_required
@admin_required
def department_list(request):
    departments = Department.objects.all()
    return render(request, "accounts/department_list.html", {"departments": departments})


@login_required
@admin_required
def department_create(request):
    form = DepartmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        dept = form.save()
        log_action(request, AuditLog.Action.CREATE, "accounts",
                   f"Created department '{dept.name}'", "Department", dept.pk)
        messages.success(request, f"Department '{dept.name}' created.")
        return redirect("accounts:department_list")
    return render(request, "accounts/department_form.html", {
        "form": form, "title": "Create Department",
    })


@login_required
@admin_required
def department_edit(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    form = DepartmentForm(request.POST or None, instance=dept)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_action(request, AuditLog.Action.UPDATE, "accounts",
                   f"Updated department '{dept.name}'", "Department", dept.pk)
        messages.success(request, f"Department '{dept.name}' updated.")
        return redirect("accounts:department_list")
    return render(request, "accounts/department_form.html", {
        "form": form, "title": "Edit Department",
    })


@login_required
@admin_required
def department_delete(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    if request.method == "POST":
        name = dept.name
        pk_val = dept.pk
        dept.delete()
        log_action(request, AuditLog.Action.DELETE, "accounts",
                   f"Deleted department '{name}'", "Department", pk_val)
        messages.success(request, "Department deleted.")
        return redirect("accounts:department_list")
    return render(request, "accounts/department_confirm_delete.html", {"dept": dept})
