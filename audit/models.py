from django.db import models
from django.conf import settings


class AuditLog(models.Model):

    class Action(models.TextChoices):
        LOGIN    = "LOGIN",    "Login"
        LOGOUT   = "LOGOUT",   "Logout"
        CREATE   = "CREATE",   "Create"
        UPDATE   = "UPDATE",   "Update"
        DELETE   = "DELETE",   "Delete"
        APPROVE  = "APPROVE",  "Approve"
        REJECT   = "REJECT",   "Reject"
        SIGN     = "SIGN",     "Sign"
        UPLOAD   = "UPLOAD",   "Upload"
        DOWNLOAD = "DOWNLOAD", "Download"
        ASSIGN   = "ASSIGN",   "Assign"
        RENEW    = "RENEW",    "Renew"
        VIEW     = "VIEW",     "View"
        CANCEL   = "CANCEL",   "Cancel"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action      = models.CharField(max_length=20, choices=Action.choices)
    module      = models.CharField(max_length=50)
    object_type = models.CharField(max_length=50, blank=True)
    object_id   = models.CharField(max_length=50, blank=True)
    description = models.TextField()
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    timestamp   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user} | {self.action} | {self.description[:50]}"


def log_action(request, action, module, description, object_type="", object_id=""):
    """Utility to create an audit log entry from a request."""
    ip = request.META.get("HTTP_X_FORWARDED_FOR")
    if ip:
        ip = ip.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")

    AuditLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action=action,
        module=module,
        object_type=object_type,
        object_id=str(object_id),
        description=description,
        ip_address=ip,
    )
