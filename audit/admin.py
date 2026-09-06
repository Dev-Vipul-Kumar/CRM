from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display  = ("user", "action", "module", "object_type", "object_id", "timestamp")
    list_filter   = ("action", "module")
    search_fields = ("user__username", "description")
    readonly_fields = ("user", "action", "module", "object_type", "object_id",
                       "description", "ip_address", "timestamp")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
