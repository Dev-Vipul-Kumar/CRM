import base64
import json
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator

from contracts.models import Contract
from .models import Signature
from accounts.decorators import manager_required
from audit.models import log_action, AuditLog
from notifications.utils import notify_signature_required


@login_required
def signature_list(request):
    user = request.user
    if user.is_admin:
        qs = Signature.objects.select_related("contract", "signer").order_by("-requested_at")
    else:
        qs = Signature.objects.filter(signer=user).select_related("contract").order_by("-requested_at")

    paginator = Paginator(qs, 15)
    page      = paginator.get_page(request.GET.get("page"))
    return render(request, "signatures/signature_list.html", {"page_obj": page})


@login_required
@manager_required
def request_signature(request, contract_pk):
    contract = get_object_or_404(Contract, pk=contract_pk)

    if contract.status not in [Contract.Status.APPROVED, Contract.Status.PENDING_SIGNATURE]:
        messages.error(request, "Contract must be Approved before requesting signatures.")
        return redirect("contracts:contract_detail", pk=contract_pk)

    if request.method == "POST":
        signer_ids = request.POST.getlist("signers")
        if not signer_ids:
            messages.error(request, "Please select at least one signer.")
        else:
            from accounts.models import User
            signers = User.objects.filter(pk__in=signer_ids, status=User.Status.ACTIVE)
            current_version = contract.current_version

            for signer in signers:
                sig, created = Signature.objects.get_or_create(
                    contract=contract,
                    signer=signer,
                    status=Signature.Status.PENDING,
                    defaults={
                        "contract_version": current_version,
                        "requested_by":     request.user,
                    }
                )
                if created:
                    notify_signature_required(contract, signer, request.user)

            contract.status = Contract.Status.PENDING_SIGNATURE
            contract.save()

            log_action(request, AuditLog.Action.SIGN, "signatures",
                       f"Signature requested for {contract.contract_number}", "Contract", contract.pk)
            messages.success(request, "Signature requests sent.")
            return redirect("contracts:contract_detail", pk=contract_pk)

    # Get users who can sign (assignments + managers)
    from accounts.models import User
    available_signers = User.objects.filter(
        status=User.Status.ACTIVE,
        contract_assignments__contract=contract,
    ).distinct()

    return render(request, "signatures/request_signature.html", {
        "contract":          contract,
        "available_signers": available_signers,
    })


@login_required
def sign_contract(request, signature_pk):
    signature = get_object_or_404(Signature, pk=signature_pk)

    # Only the intended signer can sign
    if signature.signer != request.user:
        messages.error(request, "You are not authorized to sign this document.")
        return redirect("signatures:signature_list")

    if signature.status != Signature.Status.PENDING:
        messages.error(request, "This signature request is no longer pending.")
        return redirect("signatures:signature_list")

    if request.method == "POST":
        action         = request.POST.get("action")
        signature_data = request.POST.get("signature_data", "")
        reason         = request.POST.get("rejection_reason", "")

        if action == "sign":
            if not signature_data:
                messages.error(request, "Please provide your signature.")
                return render(request, "signatures/sign_contract.html", {
                    "signature": signature,
                })

            signature.signature_data = signature_data
            signature.status          = Signature.Status.SIGNED
            signature.signed_at       = timezone.now()
            signature.ip_address      = _get_client_ip(request)
            signature.save()

            # Check if all pending signatures for this contract are done
            pending = Signature.objects.filter(
                contract=signature.contract,
                status=Signature.Status.PENDING,
            ).count()

            if pending == 0:
                signature.contract.status = Contract.Status.ACTIVE
                signature.contract.save()

            log_action(request, AuditLog.Action.SIGN, "signatures",
                       f"Signed contract {signature.contract.contract_number}", "Signature", signature.pk)
            messages.success(request, f"Contract {signature.contract.contract_number} signed successfully.")
            return redirect("signatures:signature_list")

        elif action == "reject":
            signature.status           = Signature.Status.REJECTED
            signature.rejection_reason = reason
            signature.ip_address       = _get_client_ip(request)   # record IP on rejection too
            signature.save()

            # Notify the requester that the signature was rejected
            from notifications.models import Notification
            if signature.requested_by:
                Notification.objects.create(
                    recipient=signature.requested_by,
                    title=f"Signature Rejected: {signature.contract.contract_number}",
                    message=(
                        f"{request.user.full_name} rejected the signature request "
                        f"for '{signature.contract.title}'."
                        + (f" Reason: {reason}" if reason else "")
                    ),
                    notification_type=Notification.NotificationType.CONTRACT_REJECTED,
                    contract=signature.contract,
                )

            log_action(request, AuditLog.Action.REJECT, "signatures",
                       f"Rejected signature for {signature.contract.contract_number}", "Signature", signature.pk)
            messages.warning(request, "Signature rejected.")
            return redirect("signatures:signature_list")

    return render(request, "signatures/sign_contract.html", {"signature": signature})


@login_required
def signature_detail(request, pk):
    sig = get_object_or_404(Signature, pk=pk)
    return render(request, "signatures/signature_detail.html", {"signature": sig})


def _get_client_ip(request):
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
