import os
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.conf import settings as django_settings

from .models import Contract, ContractVersion, ContractCategory, ContractAssignment
from .forms import ContractForm, ContractVersionForm, AssignmentForm, ContractCategoryForm
from accounts.decorators import manager_required, admin_required
from accounts.models import User, Department
from audit.models import log_action, AuditLog
from notifications.utils import notify_contract_update


# ─── Contract List ────────────────────────────────────────────────────────────

@login_required
def contract_list(request):
    user = request.user

    if user.is_admin:
        qs = Contract.objects.select_related("owner", "department", "contract_type")
    elif user.is_manager:
        qs = Contract.objects.filter(
            Q(owner=user) |
            Q(assignments__user=user) |
            Q(department=user.department)
        ).distinct().select_related("owner", "department", "contract_type")
    else:
        assigned_ids = ContractAssignment.objects.filter(user=user).values_list("contract_id", flat=True)
        qs = Contract.objects.filter(id__in=assigned_ids).select_related("owner", "department", "contract_type")

    # Search
    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(
            Q(contract_number__icontains=search) |
            Q(title__icontains=search) |
            Q(party_name__icontains=search)
        )

    # Filters
    status_filter   = request.GET.get("status", "")
    type_filter     = request.GET.get("contract_type", "")
    dept_filter     = request.GET.get("department", "")
    priority_filter = request.GET.get("priority", "")

    if status_filter:
        qs = qs.filter(status=status_filter)
    if type_filter:
        qs = qs.filter(contract_type_id=type_filter)
    if dept_filter:
        qs = qs.filter(department_id=dept_filter)
    if priority_filter:
        qs = qs.filter(priority=priority_filter)

    # Sorting
    sort = request.GET.get("sort", "-created_at")
    valid_sorts = ["created_at", "-created_at", "end_date", "-end_date",
                   "contract_value", "-contract_value", "contract_number", "-contract_number",
                   "updated_at", "-updated_at"]
    if sort in valid_sorts:
        qs = qs.order_by(sort)

    paginator = Paginator(qs, 15)
    page      = paginator.get_page(request.GET.get("page"))

    return render(request, "contracts/contract_list.html", {
        "page_obj":       page,
        "search":         search,
        "status_filter":  status_filter,
        "type_filter":    type_filter,
        "dept_filter":    dept_filter,
        "priority_filter": priority_filter,
        "sort":           sort,
        "statuses":       Contract.Status.choices,
        "priorities":     Contract.Priority.choices,
        "categories":     ContractCategory.objects.all(),
        "departments":    Department.objects.all(),
    })


# ─── Contract Detail ──────────────────────────────────────────────────────────

@login_required
def contract_detail(request, pk):
    contract = _get_contract_or_403(request, pk)
    versions     = contract.versions.all()
    assignments  = contract.assignments.select_related("user")
    approvals    = contract.approvals.select_related("reviewer").order_by("-created_at")
    signatures   = contract.signatures.select_related("signer").order_by("-requested_at")
    notifications = contract.notifications.filter(recipient=request.user).order_by("-created_at")[:10]

    return render(request, "contracts/contract_detail.html", {
        "contract":      contract,
        "versions":      versions,
        "assignments":   assignments,
        "approvals":     approvals,
        "signatures":    signatures,
        "notifications": notifications,
    })


# ─── Contract Create ──────────────────────────────────────────────────────────

@login_required
@manager_required
def contract_create(request):
    contract_form = ContractForm(request.POST or None)
    version_form  = ContractVersionForm(request.POST or None, request.FILES or None)

    if request.method == "POST":
        if contract_form.is_valid() and version_form.is_valid():
            document = request.FILES.get("document")
            if document:
                error = _validate_document(document)
                if error:
                    messages.error(request, error)
                    return render(request, "contracts/contract_form.html", {
                        "contract_form": contract_form,
                        "version_form":  version_form,
                        "title": "Create Contract",
                    })

            contract = contract_form.save(commit=False)
            contract.created_by = request.user
            contract.save()

            # Create Version 1
            version = ContractVersion(
                contract=contract,
                version_number=1,
                created_by=request.user,
                change_summary=version_form.cleaned_data.get("change_summary") or "Initial version",
                is_current=True,
            )
            if document:
                version.document = document
            version.save()

            log_action(request, AuditLog.Action.CREATE, "contracts",
                       f"Created contract {contract.contract_number}", "Contract", contract.pk)

            messages.success(request, f"Contract {contract.contract_number} created successfully.")
            return redirect("contracts:contract_detail", pk=contract.pk)

    return render(request, "contracts/contract_form.html", {
        "contract_form": contract_form,
        "version_form":  version_form,
        "title": "Create Contract",
        "action": "Create",
    })


# ─── Contract Edit ────────────────────────────────────────────────────────────

@login_required
@manager_required
def contract_edit(request, pk):
    contract = _get_contract_or_403(request, pk)
    form = ContractForm(request.POST or None, instance=contract)

    if request.method == "POST" and form.is_valid():
        form.save()
        log_action(request, AuditLog.Action.UPDATE, "contracts",
                   f"Updated contract {contract.contract_number}", "Contract", contract.pk)
        notify_contract_update(contract, request.user)
        messages.success(request, f"Contract {contract.contract_number} updated.")
        return redirect("contracts:contract_detail", pk=pk)

    return render(request, "contracts/contract_form.html", {
        "contract_form": form,
        "title":         "Edit Contract",
        "action":        "Save Changes",
        "contract":      contract,
    })


# ─── Upload new version ───────────────────────────────────────────────────────

@login_required
@manager_required
def contract_upload_version(request, pk):
    contract = _get_contract_or_403(request, pk)
    form     = ContractVersionForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        document = request.FILES.get("document")
        if document:
            error = _validate_document(document)
            if error:
                messages.error(request, error)
                return redirect("contracts:contract_versions", pk=pk)

        last_version = contract.versions.order_by("-version_number").first()
        next_num     = (last_version.version_number + 1) if last_version else 1

        version = ContractVersion(
            contract=contract,
            version_number=next_num,
            created_by=request.user,
            change_summary=form.cleaned_data.get("change_summary", ""),
            is_current=True,
        )
        if document:
            version.document = document
        version.save()

        log_action(request, AuditLog.Action.UPLOAD, "contracts",
                   f"Uploaded version {next_num} of {contract.contract_number}", "ContractVersion", version.pk)
        notify_contract_update(contract, request.user)
        messages.success(request, f"Version {next_num} uploaded successfully.")
        return redirect("contracts:contract_versions", pk=pk)

    return render(request, "contracts/upload_version.html", {
        "form":     form,
        "contract": contract,
    })


# ─── Version history ──────────────────────────────────────────────────────────

@login_required
def contract_versions(request, pk):
    contract = _get_contract_or_403(request, pk)
    versions = contract.versions.select_related("created_by").order_by("-version_number")
    return render(request, "contracts/contract_versions.html", {
        "contract": contract,
        "versions": versions,
    })


# ─── Document download ────────────────────────────────────────────────────────

@login_required
def download_document(request, version_pk):
    version  = get_object_or_404(ContractVersion, pk=version_pk)
    contract = version.contract
    _check_contract_access(request.user, contract)

    if not version.document:
        raise Http404("No document attached to this version.")

    file_path = version.document.path
    if not os.path.exists(file_path):
        raise Http404("Document file not found.")

    log_action(request, AuditLog.Action.DOWNLOAD, "contracts",
               f"Downloaded version {version.version_number} of {contract.contract_number}",
               "ContractVersion", version.pk)

    return FileResponse(open(file_path, "rb"), as_attachment=True, filename=os.path.basename(file_path))


# ─── Assignment ───────────────────────────────────────────────────────────────

@login_required
@manager_required
def contract_assign(request, pk):
    contract = _get_contract_or_403(request, pk)
    current_user_ids = list(contract.assignments.values_list("user_id", flat=True))

    if request.method == "POST":
        form = AssignmentForm(request.POST)
        if form.is_valid():
            new_users = form.cleaned_data["users"]
            notes     = form.cleaned_data.get("notes", "")

            # Track who is newly being assigned (didn't have assignment before)
            existing_ids   = set(contract.assignments.values_list("user_id", flat=True))
            new_user_ids   = {u.pk for u in new_users}
            newly_assigned = [u for u in new_users if u.pk not in existing_ids]

            # Remove assignments not in new list
            contract.assignments.exclude(user__in=new_users).delete()

            # Add new assignments or update notes on existing ones
            for u in new_users:
                obj, created = ContractAssignment.objects.get_or_create(
                    contract=contract,
                    user=u,
                    defaults={"assigned_by": request.user, "notes": notes},
                )
                if not created and notes:
                    # Update notes on re-submitted assignments
                    obj.notes = notes
                    obj.save(update_fields=["notes"])

            # Notify newly assigned users
            if newly_assigned:
                from notifications.utils import notify_contract_update
                for u in newly_assigned:
                    from notifications.models import Notification
                    Notification.objects.create(
                        recipient=u,
                        title=f"Contract Assigned: {contract.contract_number}",
                        message=f"You have been assigned to contract '{contract.title}'.",
                        notification_type=Notification.NotificationType.ASSIGNMENT,
                        contract=contract,
                    )

            log_action(request, AuditLog.Action.ASSIGN, "contracts",
                       f"Updated assignments for {contract.contract_number} "
                       f"({len(new_users)} user(s))", "Contract", contract.pk)
            messages.success(request, "Contract assignments updated.")
            return redirect("contracts:contract_detail", pk=pk)
    else:
        from accounts.models import User as UserModel
        form = AssignmentForm(initial={
            "users": UserModel.objects.filter(id__in=current_user_ids)
        })

    return render(request, "contracts/contract_assign.html", {
        "form":     form,
        "contract": contract,
    })


# ─── Archive/Cancel ───────────────────────────────────────────────────────────

@login_required
@admin_required
def contract_archive(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    if request.method == "POST":
        contract.status = Contract.Status.ARCHIVED
        contract.save()
        log_action(request, AuditLog.Action.UPDATE, "contracts",
                   f"Archived contract {contract.contract_number}", "Contract", contract.pk)
        messages.success(request, f"Contract {contract.contract_number} archived.")
    return redirect("contracts:contract_detail", pk=pk)


@login_required
@manager_required
def contract_renew(request, pk):
    """Mark a contract as Renewed and create a fresh version starting today."""
    contract = get_object_or_404(Contract, pk=pk)
    allowed_statuses = [
        Contract.Status.ACTIVE,
        Contract.Status.EXPIRING_SOON,
        Contract.Status.EXPIRED,
    ]
    if contract.status not in allowed_statuses:
        messages.error(request, "Only Active, Expiring Soon or Expired contracts can be renewed.")
        return redirect("contracts:contract_detail", pk=pk)

    if request.method == "POST":
        from django.utils import timezone
        import datetime

        new_end_date = request.POST.get("new_end_date", "")
        if not new_end_date:
            messages.error(request, "Please provide a new end date for the renewal.")
            return redirect("contracts:contract_detail", pk=pk)

        try:
            from datetime import date
            end_date = date.fromisoformat(new_end_date)
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect("contracts:contract_detail", pk=pk)

        old_end = contract.end_date
        contract.end_date     = end_date
        contract.renewal_date = timezone.now().date()
        contract.status       = Contract.Status.RENEWED
        contract.save()

        # Create a new version to record the renewal
        last_version = contract.versions.order_by("-version_number").first()
        next_num     = (last_version.version_number + 1) if last_version else 1
        ContractVersion.objects.create(
            contract=contract,
            version_number=next_num,
            created_by=request.user,
            change_summary=f"Contract renewed. Previous end date: {old_end}. New end date: {end_date}.",
            is_current=True,
        )

        log_action(request, AuditLog.Action.RENEW, "contracts",
                   f"Renewed contract {contract.contract_number} — new end: {end_date}",
                   "Contract", contract.pk)
        from notifications.utils import notify_contract_update
        notify_contract_update(contract, request.user)
        messages.success(request, f"Contract {contract.contract_number} renewed until {end_date}.")

    return redirect("contracts:contract_detail", pk=pk)


@login_required
@manager_required
def contract_cancel(request, pk):
    """Mark a contract as Cancelled."""
    contract = get_object_or_404(Contract, pk=pk)
    uncancellable = [
        Contract.Status.ARCHIVED,
        Contract.Status.CANCELLED,
        Contract.Status.EXPIRED,
    ]
    if contract.status in uncancellable:
        messages.error(request, f"Cannot cancel a contract that is {contract.get_status_display()}.")
        return redirect("contracts:contract_detail", pk=pk)

    if request.method == "POST":
        reason = request.POST.get("cancel_reason", "")
        contract.status = Contract.Status.CANCELLED
        contract.save()

        log_action(request, AuditLog.Action.UPDATE, "contracts",
                   f"Cancelled contract {contract.contract_number}"
                   + (f" — reason: {reason}" if reason else ""),
                   "Contract", contract.pk)
        from notifications.utils import notify_contract_update
        notify_contract_update(contract, request.user)
        messages.success(request, f"Contract {contract.contract_number} has been cancelled.")

    return redirect("contracts:contract_detail", pk=pk)


# ─── Contract Categories (admin) ──────────────────────────────────────────────

@login_required
@admin_required
def category_list(request):
    categories = ContractCategory.objects.all()
    return render(request, "contracts/category_list.html", {"categories": categories})


@login_required
@admin_required
def category_create(request):
    form = ContractCategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        cat = form.save()
        log_action(request, AuditLog.Action.CREATE, "contracts",
                   f"Created contract category '{cat.name}'", "ContractCategory", cat.pk)
        messages.success(request, f"Category '{cat.name}' created.")
        return redirect("contracts:category_list")
    return render(request, "contracts/category_form.html", {"form": form, "title": "Create Category"})


@login_required
@admin_required
def category_edit(request, pk):
    cat  = get_object_or_404(ContractCategory, pk=pk)
    form = ContractCategoryForm(request.POST or None, instance=cat)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_action(request, AuditLog.Action.UPDATE, "contracts",
                   f"Updated contract category '{cat.name}'", "ContractCategory", cat.pk)
        messages.success(request, f"Category '{cat.name}' updated.")
        return redirect("contracts:category_list")
    return render(request, "contracts/category_form.html", {"form": form, "title": "Edit Category"})


@login_required
@admin_required
def category_delete(request, pk):
    cat = get_object_or_404(ContractCategory, pk=pk)
    if request.method == "POST":
        name   = cat.name
        pk_val = cat.pk
        cat.delete()
        log_action(request, AuditLog.Action.DELETE, "contracts",
                   f"Deleted contract category '{name}'", "ContractCategory", pk_val)
        messages.success(request, "Category deleted.")
        return redirect("contracts:category_list")
    return render(request, "contracts/category_confirm_delete.html", {"cat": cat})


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_contract_or_403(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    _check_contract_access(request.user, contract)
    return contract


def _check_contract_access(user, contract):
    from django.core.exceptions import PermissionDenied
    if user.is_admin:
        return
    if user.is_manager and (
        contract.owner == user or
        contract.department == user.department or
        contract.assignments.filter(user=user).exists()
    ):
        return
    if contract.assignments.filter(user=user).exists():
        return
    raise PermissionDenied


def _validate_document(document):
    ext = os.path.splitext(document.name)[1].lower()
    allowed = django_settings.ALLOWED_DOCUMENT_EXTENSIONS
    if ext not in allowed:
        return f"Invalid file type. Allowed: {', '.join(allowed)}"
    if document.size > django_settings.MAX_UPLOAD_SIZE:
        return f"File too large. Maximum size is {django_settings.MAX_UPLOAD_SIZE // (1024*1024)} MB."
    return None
