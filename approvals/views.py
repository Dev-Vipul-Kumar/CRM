from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator

from contracts.models import Contract
from .models import Approval
from .forms import ApprovalActionForm, SubmitForReviewForm
from accounts.decorators import manager_required
from audit.models import log_action, AuditLog
from notifications.utils import (
    notify_approval_required,
    notify_contract_approved,
    notify_contract_rejected,
)


@login_required
def approval_list(request):
    user = request.user
    if user.is_admin:
        qs = Approval.objects.select_related("contract", "reviewer").order_by("-created_at")
    elif user.is_manager:
        qs = Approval.objects.filter(reviewer=user).select_related("contract", "reviewer").order_by("-created_at")
    else:
        qs = Approval.objects.none()

    paginator = Paginator(qs, 15)
    page      = paginator.get_page(request.GET.get("page"))

    # Contracts pending approval (for managers/admins to act on)
    pending_contracts = Contract.objects.filter(status=Contract.Status.PENDING_APPROVAL)
    if user.is_manager:
        from django.db.models import Q
        pending_contracts = pending_contracts.filter(
            Q(department=user.department) | Q(owner=user)
        )

    return render(request, "approvals/approval_list.html", {
        "page_obj":         page,
        "pending_contracts": pending_contracts,
    })


@login_required
@manager_required
def submit_for_review(request, contract_pk):
    contract = get_object_or_404(Contract, pk=contract_pk)

    if contract.status not in [Contract.Status.DRAFT, Contract.Status.REJECTED,
                               Contract.Status.UNDER_REVIEW]:
        messages.error(request, "This contract cannot be submitted for review at this stage.")
        return redirect("contracts:contract_detail", pk=contract_pk)

    form = SubmitForReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        contract.status = Contract.Status.PENDING_APPROVAL
        contract.save()

        Approval.objects.create(
            contract=contract,
            reviewer=request.user,
            action=Approval.Action.SUBMITTED,
            comment=form.cleaned_data.get("comment", ""),
        )

        log_action(request, AuditLog.Action.UPDATE, "approvals",
                   f"Submitted {contract.contract_number} for approval", "Contract", contract.pk)
        notify_approval_required(contract, request.user)
        messages.success(request, f"Contract {contract.contract_number} submitted for approval.")
        return redirect("contracts:contract_detail", pk=contract_pk)

    return render(request, "approvals/submit_for_review.html", {
        "form":     form,
        "contract": contract,
    })


@login_required
@manager_required
def approval_action(request, contract_pk):
    contract = get_object_or_404(Contract, pk=contract_pk)

    if contract.status != Contract.Status.PENDING_APPROVAL:
        messages.error(request, "This contract is not pending approval.")
        return redirect("contracts:contract_detail", pk=contract_pk)

    form = ApprovalActionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        action  = form.cleaned_data["action"]
        comment = form.cleaned_data.get("comment", "")

        Approval.objects.create(
            contract=contract,
            reviewer=request.user,
            action=action,
            comment=comment,
        )

        if action == Approval.Action.APPROVED:
            contract.status = Contract.Status.APPROVED
            notify_contract_approved(contract, request.user)
            msg = f"Contract {contract.contract_number} approved."
        elif action == Approval.Action.REJECTED:
            contract.status = Contract.Status.REJECTED
            notify_contract_rejected(contract, request.user)
            msg = f"Contract {contract.contract_number} rejected."
        else:
            contract.status = Contract.Status.UNDER_REVIEW
            msg = f"Changes requested for {contract.contract_number}."

        contract.save()

        # Map approval action to audit log action safely
        audit_action_map = {
            Approval.Action.APPROVED:          AuditLog.Action.APPROVE,
            Approval.Action.REJECTED:          AuditLog.Action.REJECT,
            Approval.Action.CHANGES_REQUESTED: AuditLog.Action.UPDATE,
        }
        audit_action = audit_action_map.get(action, AuditLog.Action.UPDATE)
        log_action(request, audit_action, "approvals",
                   f"{action} on contract {contract.contract_number}", "Contract", contract.pk)
        messages.success(request, msg)
        return redirect("contracts:contract_detail", pk=contract_pk)

    return render(request, "approvals/approval_action.html", {
        "form":     form,
        "contract": contract,
    })


@login_required
def approval_detail(request, pk):
    approval = get_object_or_404(Approval, pk=pk)
    return render(request, "approvals/approval_detail.html", {"approval": approval})
