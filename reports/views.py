from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Q, Count, Sum
from django.utils import timezone
import csv
from datetime import date

from contracts.models import Contract, ContractCategory
from accounts.models import Department
from accounts.decorators import manager_required
from audit.models import log_action, AuditLog


@login_required
@manager_required
def reports_index(request):
    user  = request.user
    today = timezone.now().date()

    # Contracts queryset based on role
    if user.is_admin:
        qs = Contract.objects.all()
    else:
        qs = Contract.objects.filter(
            Q(owner=user) | Q(assignments__user=user) | Q(department=user.department)
        ).distinct()

    # Counts by status
    status_counts = {
        label: qs.filter(status=value).count()
        for value, label in Contract.Status.choices
    }

    # Expiring in 30 days
    expiring_soon = qs.filter(
        end_date__gte=today,
        end_date__lte=today + _delta(30),
        status__in=[Contract.Status.ACTIVE, Contract.Status.EXPIRING_SOON],
    ).order_by("end_date")

    # By category
    by_category = (
        qs.values("contract_type__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # By department
    by_department = (
        qs.values("department__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    return render(request, "reports/reports_index.html", {
        "status_counts":  status_counts,
        "expiring_soon":  expiring_soon,
        "by_category":    by_category,
        "by_department":  by_department,
        "total":          qs.count(),
    })


@login_required
@manager_required
def export_contracts_csv(request):
    user = request.user
    if user.is_admin:
        qs = Contract.objects.select_related("owner", "department", "contract_type").order_by("contract_number")
    else:
        qs = Contract.objects.filter(
            Q(owner=user) | Q(assignments__user=user) | Q(department=user.department)
        ).distinct().select_related("owner", "department", "contract_type").order_by("contract_number")

    # Optional filters from query params
    status = request.GET.get("status")
    if status:
        qs = qs.filter(status=status)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="contracts_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Contract Number", "Title", "Type", "Status", "Priority",
        "Party Name", "Department", "Owner",
        "Start Date", "End Date", "Renewal Date",
        "Contract Value", "Payment Terms", "Created At",
    ])

    rows = list(qs)   # evaluate once
    for c in rows:
        writer.writerow([
            c.contract_number,
            c.title,
            c.contract_type.name if c.contract_type else "",
            c.get_status_display(),
            c.get_priority_display(),
            c.party_name,
            c.department.name if c.department else "",
            c.owner.username if c.owner else "",
            c.start_date,
            c.end_date,
            c.renewal_date or "",
            c.contract_value or "",
            c.payment_terms,
            c.created_at.strftime("%Y-%m-%d %H:%M"),
        ])

    # Audit log the export
    log_action(request, AuditLog.Action.DOWNLOAD, "reports",
               f"Exported {len(rows)} contract(s) to CSV"
               + (f" (status filter: {status})" if status else ""),
               "Contract", "csv")

    return response


def _delta(days):
    import datetime
    return datetime.timedelta(days=days)
