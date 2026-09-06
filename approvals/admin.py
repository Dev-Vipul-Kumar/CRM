from django.contrib import admin
from .models import Approval


@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    list_display  = ("contract", "reviewer", "action", "created_at")
    list_filter   = ("action",)
    search_fields = ("contract__contract_number",)
