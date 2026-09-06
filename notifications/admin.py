from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ("recipient", "title", "notification_type", "status", "created_at")
    list_filter   = ("notification_type", "status")
    search_fields = ("recipient__username", "title")
