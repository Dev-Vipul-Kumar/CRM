from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count, Q

from contracts.models import Contract, ContractAssignment
from notifications.models import Notification
from approvals.models import Approval
from signatures.models import Signature
from audit.models import AuditLog


@login_required
def dashboard(request):
    user = request.user
    today = timezone.now().date()

    if user.is_admin:
        return _admin_dashboard(request, today)
    elif user.is_manager:
        return _manager_dashboard(request, today, user)
    else:
        return _employee_dashboard(request, today, user)


def _admin_dashboard(request, today):
    contracts = Contract.objects.all()

    stats = {
        "total_contracts":    contracts.count(),
        "active":             contracts.filter(status=Contract.Status.ACTIVE).count(),
        "expiring_soon":      contracts.filter(status=Contract.Status.EXPIRING_SOON).count(),
        "expired":            contracts.filter(status=Contract.Status.EXPIRED).count(),
        "pending_approval":   contracts.filter(status=Contract.Status.PENDING_APPROVAL).count(),
        "pending_signature":  contracts.filter(status=Contract.Status.PENDING_SIGNATURE).count(),
        "draft":              contracts.filter(status=Contract.Status.DRAFT).count(),
        "total_users":        _user_count(),
    }

    recent_contracts    = contracts.select_related("owner", "department").order_by("-created_at")[:8]
    recent_approvals    = Approval.objects.select_related("contract", "reviewer").order_by("-created_at")[:5]
    recent_signatures   = Signature.objects.select_related("contract", "signer").order_by("-requested_at")[:5]
    recent_activities   = AuditLog.objects.select_related("user").order_by("-timestamp")[:10]
    upcoming_expirations = contracts.filter(
        end_date__gte=today,
        end_date__lte=today + _timedelta(30),
        status__in=[Contract.Status.ACTIVE, Contract.Status.EXPIRING_SOON],
    ).order_by("end_date")[:10]

    unread_notifications = Notification.objects.filter(
        recipient=request.user,
        status=Notification.Status.UNREAD,
    ).count()

    return render(request, "dashboard/admin_dashboard.html", {
        "stats":               stats,
        "recent_contracts":    recent_contracts,
        "recent_approvals":    recent_approvals,
        "recent_signatures":   recent_signatures,
        "recent_activities":   recent_activities,
        "upcoming_expirations": upcoming_expirations,
        "unread_notifications": unread_notifications,
    })


def _manager_dashboard(request, today, user):
    contracts = Contract.objects.filter(
        Q(owner=user) |
        Q(department=user.department) |
        Q(assignments__user=user)
    ).distinct()

    stats = {
        "total_contracts":   contracts.count(),
        "active":            contracts.filter(status=Contract.Status.ACTIVE).count(),
        "expiring_soon":     contracts.filter(status=Contract.Status.EXPIRING_SOON).count(),
        "pending_approval":  contracts.filter(status=Contract.Status.PENDING_APPROVAL).count(),
        "pending_signature": contracts.filter(status=Contract.Status.PENDING_SIGNATURE).count(),
        "draft":             contracts.filter(status=Contract.Status.DRAFT).count(),
    }

    recent_contracts     = contracts.select_related("owner", "department").order_by("-created_at")[:8]
    pending_approvals    = contracts.filter(status=Contract.Status.PENDING_APPROVAL)[:5]
    upcoming_expirations = contracts.filter(
        end_date__gte=today,
        end_date__lte=today + _timedelta(30),
    ).order_by("end_date")[:8]

    unread_notifications = Notification.objects.filter(
        recipient=user,
        status=Notification.Status.UNREAD,
    ).count()

    return render(request, "dashboard/manager_dashboard.html", {
        "stats":               stats,
        "recent_contracts":    recent_contracts,
        "pending_approvals":   pending_approvals,
        "upcoming_expirations": upcoming_expirations,
        "unread_notifications": unread_notifications,
    })


def _employee_dashboard(request, today, user):
    assigned_ids = ContractAssignment.objects.filter(user=user).values_list("contract_id", flat=True)
    contracts    = Contract.objects.filter(id__in=assigned_ids)

    stats = {
        "total_contracts":  contracts.count(),
        "active":           contracts.filter(status=Contract.Status.ACTIVE).count(),
        "expiring_soon":    contracts.filter(status=Contract.Status.EXPIRING_SOON).count(),
        "pending_signature": Signature.objects.filter(signer=user, status=Signature.Status.PENDING).count(),
    }

    recent_contracts     = contracts.select_related("owner", "department").order_by("-created_at")[:6]
    pending_signatures   = Signature.objects.filter(
        signer=user, status=Signature.Status.PENDING
    ).select_related("contract")[:5]
    upcoming_expirations = contracts.filter(
        end_date__gte=today,
        end_date__lte=today + _timedelta(30),
    ).order_by("end_date")[:5]

    unread_notifications = Notification.objects.filter(
        recipient=user,
        status=Notification.Status.UNREAD,
    ).count()

    return render(request, "dashboard/employee_dashboard.html", {
        "stats":               stats,
        "recent_contracts":    recent_contracts,
        "pending_signatures":  pending_signatures,
        "upcoming_expirations": upcoming_expirations,
        "unread_notifications": unread_notifications,
    })


def _user_count():
    from accounts.models import User
    return User.objects.count()


def _timedelta(days):
    import datetime
    return datetime.timedelta(days=days)
