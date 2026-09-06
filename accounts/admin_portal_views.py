"""
Admin Portal Views
------------------
Dedicated admin control-centre — separate from the regular dashboard.
Accessible at /admin-portal/ only by users with role=ADMIN.
"""

import datetime
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Q, Count, Sum

from .models import User, Department
from .forms import UserCreateForm, UserEditForm, PasswordResetForm, DepartmentForm
from .decorators import admin_required
from contracts.models import Contract, ContractCategory, ContractVersion
from approvals.models import Approval
from signatures.models import Signature
from notifications.models import Notification
from audit.models import AuditLog, log_action


# ── Main portal view ──────────────────────────────────────────────────────────

@login_required
@admin_required
def admin_portal(request):
    today = timezone.now().date()

    # ── Contract stats ──
    contracts = Contract.objects.all()
    contract_stats = {
        "total":             contracts.count(),
        "active":            contracts.filter(status=Contract.Status.ACTIVE).count(),
        "draft":             contracts.filter(status=Contract.Status.DRAFT).count(),
        "expiring_soon":     contracts.filter(status=Contract.Status.EXPIRING_SOON).count(),
        "expired":           contracts.filter(status=Contract.Status.EXPIRED).count(),
        "pending_approval":  contracts.filter(status=Contract.Status.PENDING_APPROVAL).count(),
        "pending_signature": contracts.filter(status=Contract.Status.PENDING_SIGNATURE).count(),
        "approved":          contracts.filter(status=Contract.Status.APPROVED).count(),
        "total_value":       contracts.aggregate(v=Sum("contract_value"))["v"] or 0,
    }

    # ── User stats ──
    users = User.objects.all()
    user_stats = {
        "total":     users.count(),
        "active":    users.filter(status=User.Status.ACTIVE).count(),
        "inactive":  users.filter(status=User.Status.INACTIVE).count(),
        "suspended": users.filter(status=User.Status.SUSPENDED).count(),
        "admins":    users.filter(role=User.Role.ADMIN).count(),
        "managers":  users.filter(role=User.Role.MANAGER).count(),
        "employees": users.filter(role=User.Role.EMPLOYEE).count(),
    }

    # ── Recent data ──
    recent_users       = users.select_related("department").order_by("-date_joined")[:8]
    recent_contracts   = contracts.select_related("owner", "department", "contract_type").order_by("-created_at")[:8]
    recent_activities  = AuditLog.objects.select_related("user").order_by("-timestamp")[:12]
    recent_approvals   = Approval.objects.select_related("contract", "reviewer").order_by("-created_at")[:6]
    recent_signatures  = Signature.objects.select_related("contract", "signer").order_by("-requested_at")[:6]

    # ── Expiring / Expired ──
    expiring = contracts.filter(
        end_date__gte=today,
        end_date__lte=today + datetime.timedelta(days=30),
        status__in=[Contract.Status.ACTIVE, Contract.Status.EXPIRING_SOON],
    ).order_by("end_date")[:10]

    expired_recent = contracts.filter(
        status=Contract.Status.EXPIRED,
    ).order_by("-end_date")[:6]

    # ── Department stats ──
    departments = Department.objects.annotate(
        user_count=Count("users", distinct=True),
        contract_count=Count("contracts", distinct=True),
    ).order_by("name")

    # ── Categories ──
    categories = ContractCategory.objects.annotate(
        count=Count("contracts")
    ).order_by("-count")

    # ── Unread notifications for admin ──
    unread_count = Notification.objects.filter(
        recipient=request.user,
        status=Notification.Status.UNREAD,
    ).count()

    return render(request, "admin_portal/portal.html", {
        "contract_stats":   contract_stats,
        "user_stats":       user_stats,
        "recent_users":     recent_users,
        "recent_contracts": recent_contracts,
        "recent_activities": recent_activities,
        "recent_approvals": recent_approvals,
        "recent_signatures": recent_signatures,
        "expiring":         expiring,
        "expired_recent":   expired_recent,
        "departments":      departments,
        "categories":       categories,
        "unread_count":     unread_count,
        "all_users":        users.select_related("department").order_by("username"),
    })


# ── User management from portal ───────────────────────────────────────────────

@login_required
@admin_required
def portal_user_create(request):
    form = UserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        log_action(request, AuditLog.Action.CREATE, "accounts",
                   f"Admin portal: created user '{user.username}'", "User", user.pk)
        messages.success(request, f"User '{user.username}' created successfully.")
        return redirect("accounts:admin_portal")
    return render(request, "admin_portal/user_form.html", {
        "form":   form,
        "title":  "Create New User",
        "action": "Create User",
    })


@login_required
@admin_required
def portal_user_edit(request, pk):
    target = get_object_or_404(User, pk=pk)
    form   = UserEditForm(request.POST or None, instance=target)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_action(request, AuditLog.Action.UPDATE, "accounts",
                   f"Admin portal: updated user '{target.username}'", "User", target.pk)
        messages.success(request, f"User '{target.username}' updated.")
        return redirect("accounts:admin_portal")
    return render(request, "admin_portal/user_form.html", {
        "form":        form,
        "title":       f"Edit User — {target.username}",
        "action":      "Save Changes",
        "target_user": target,
    })


@login_required
@admin_required
def portal_user_toggle(request, pk):
    target = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        if target.status == User.Status.ACTIVE:
            target.status = User.Status.INACTIVE
            msg = f"User '{target.username}' deactivated."
        else:
            target.status = User.Status.ACTIVE
            msg = f"User '{target.username}' activated."
        target.save()
        log_action(request, AuditLog.Action.UPDATE, "accounts",
                   f"Admin portal: toggled status of '{target.username}' → {target.status}", "User", target.pk)
        messages.success(request, msg)
    return redirect("accounts:admin_portal")


@login_required
@admin_required
def portal_user_delete(request, pk):
    target = get_object_or_404(User, pk=pk)
    if target == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect("accounts:admin_portal")
    if request.method == "POST":
        username = target.username
        target.delete()
        log_action(request, AuditLog.Action.DELETE, "accounts",
                   f"Admin portal: deleted user '{username}'", "User", pk)
        messages.success(request, f"User '{username}' deleted.")
    return redirect("accounts:admin_portal")


@login_required
@admin_required
def portal_reset_password(request, pk):
    target = get_object_or_404(User, pk=pk)
    form   = PasswordResetForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        target.set_password(form.cleaned_data["new_password1"])
        target.save()
        log_action(request, AuditLog.Action.UPDATE, "accounts",
                   f"Admin portal: reset password for '{target.username}'", "User", target.pk)
        messages.success(request, f"Password for '{target.username}' reset.")
        return redirect("accounts:admin_portal")
    return render(request, "admin_portal/reset_password.html", {
        "form":        form,
        "target_user": target,
    })


@login_required
@admin_required
def portal_user_role_change(request, pk):
    """Quick inline role change from portal user table."""
    target = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        new_role = request.POST.get("role")
        if new_role in [r[0] for r in User.Role.choices]:
            old_role    = target.role
            target.role = new_role
            target.save()
            log_action(request, AuditLog.Action.UPDATE, "accounts",
                       f"Admin portal: changed role of '{target.username}' from {old_role} to {new_role}",
                       "User", target.pk)
            messages.success(request, f"Role for '{target.username}' updated to {new_role}.")
        else:
            messages.error(request, "Invalid role.")
    return redirect("accounts:admin_portal")


# ── Department management from portal ─────────────────────────────────────────

@login_required
@admin_required
def portal_dept_create(request):
    form = DepartmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        dept = form.save()
        log_action(request, AuditLog.Action.CREATE, "accounts",
                   f"Admin portal: created department '{dept.name}'", "Department", dept.pk)
        messages.success(request, f"Department '{dept.name}' created.")
        return redirect("accounts:admin_portal")
    return render(request, "admin_portal/dept_form.html", {
        "form": form, "title": "Create Department",
    })


@login_required
@admin_required
def portal_dept_edit(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    form = DepartmentForm(request.POST or None, instance=dept)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_action(request, AuditLog.Action.UPDATE, "accounts",
                   f"Admin portal: updated department '{dept.name}'", "Department", dept.pk)
        messages.success(request, f"Department '{dept.name}' updated.")
        return redirect("accounts:admin_portal")
    return render(request, "admin_portal/dept_form.html", {
        "form": form, "title": f"Edit Department — {dept.name}",
    })


@login_required
@admin_required
def portal_dept_delete(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    if request.method == "POST":
        name   = dept.name
        pk_val = dept.pk
        dept.delete()
        log_action(request, AuditLog.Action.DELETE, "accounts",
                   f"Admin portal: deleted department '{name}'", "Department", pk_val)
        messages.success(request, "Department deleted.")
    return redirect("accounts:admin_portal")
