from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator

from .models import AuditLog
from accounts.decorators import admin_required


@login_required
@admin_required
def audit_list(request):
    qs = AuditLog.objects.select_related("user").order_by("-timestamp")

    # Filters
    action_filter = request.GET.get("action", "")
    user_filter   = request.GET.get("user", "")
    module_filter = request.GET.get("module", "")
    search        = request.GET.get("search", "").strip()

    if action_filter:
        qs = qs.filter(action=action_filter)
    if user_filter:
        qs = qs.filter(user__username__icontains=user_filter)
    if module_filter:
        qs = qs.filter(module=module_filter)
    if search:
        qs = qs.filter(description__icontains=search)

    paginator = Paginator(qs, 25)
    page      = paginator.get_page(request.GET.get("page"))

    return render(request, "audit/audit_list.html", {
        "page_obj":     page,
        "action_filter": action_filter,
        "user_filter":  user_filter,
        "module_filter": module_filter,
        "search":       search,
        "actions":      AuditLog.Action.choices,
    })


@login_required
@admin_required
def audit_detail(request, pk):
    log = get_object_or_404(AuditLog, pk=pk)
    return render(request, "audit/audit_detail.html", {"log": log})


@login_required
def contract_activity(request, contract_pk):
    """Activity timeline for a specific contract — visible to assigned users."""
    from contracts.models import Contract
    from contracts.views import _check_contract_access
    contract = get_object_or_404(Contract, pk=contract_pk)
    _check_contract_access(request.user, contract)

    logs = AuditLog.objects.filter(
        object_type="Contract",
        object_id=str(contract_pk),
    ).select_related("user").order_by("-timestamp")[:50]

    return render(request, "audit/contract_activity.html", {
        "contract": contract,
        "logs":     logs,
    })
