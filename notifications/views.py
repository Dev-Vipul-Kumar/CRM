from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.utils import timezone

from .models import Notification
from audit.models import AuditLog


@login_required
def notification_list(request):
    qs = Notification.objects.filter(recipient=request.user).order_by("-created_at")

    status_filter = request.GET.get("status", "")
    if status_filter:
        qs = qs.filter(status=status_filter)

    paginator    = Paginator(qs, 20)
    page         = paginator.get_page(request.GET.get("page"))
    unread_count = Notification.objects.filter(
        recipient=request.user,
        status=Notification.Status.UNREAD,
    ).count()

    return render(request, "notifications/notification_list.html", {
        "page_obj":      page,
        "unread_count":  unread_count,
        "status_filter": status_filter,
        "statuses":      Notification.Status.choices,
    })


@login_required
def mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.mark_read()   # model method sets read_at + saves
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        from django.http import JsonResponse
        return JsonResponse({"status": "ok"})
    next_url = request.GET.get("next", "notifications:notification_list")
    return redirect(next_url)


@login_required
def mark_all_read(request):
    if request.method == "POST":
        now = timezone.now()
        count = Notification.objects.filter(
            recipient=request.user,
            status=Notification.Status.UNREAD,
        ).update(status=Notification.Status.READ, read_at=now)
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.UPDATE,
            module="notifications",
            object_type="Notification",
            object_id="all",
            description=f"Marked {count} notification(s) as read",
        )
        messages.success(request, "All notifications marked as read.")
    return redirect("notifications:notification_list")


@login_required
def archive_notification(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if request.method == "POST":
        notification.status      = Notification.Status.ARCHIVED
        notification.archived_at = timezone.now()
        notification.save(update_fields=["status", "archived_at"])
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.UPDATE,
            module="notifications",
            object_type="Notification",
            object_id=str(notification.pk),
            description=f"Archived notification: {notification.title[:60]}",
        )
    return redirect("notifications:notification_list")
