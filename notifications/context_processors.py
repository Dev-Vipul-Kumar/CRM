from .models import Notification


def unread_notifications(request):
    """Inject unread notification count into every template context."""
    if request.user.is_authenticated:
        count = Notification.objects.filter(
            recipient=request.user,
            status=Notification.Status.UNREAD,
        ).count()
        return {"unread_notification_count": count}
    return {"unread_notification_count": 0}
