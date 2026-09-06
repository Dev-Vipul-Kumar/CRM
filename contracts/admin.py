from django.contrib import admin
from .models import Contract, ContractVersion, ContractCategory, ContractAssignment


@admin.register(ContractCategory)
class ContractCategoryAdmin(admin.ModelAdmin):
    list_display  = ("name", "description", "created_at")
    search_fields = ("name",)


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display  = ("contract_number", "title", "status", "priority", "owner", "end_date")
    list_filter   = ("status", "priority", "department", "contract_type")
    search_fields = ("contract_number", "title", "party_name")
    readonly_fields = ("contract_number", "created_at", "updated_at")


@admin.register(ContractVersion)
class ContractVersionAdmin(admin.ModelAdmin):
    list_display  = ("contract", "version_number", "is_current", "created_by", "created_at")
    list_filter   = ("is_current",)


@admin.register(ContractAssignment)
class ContractAssignmentAdmin(admin.ModelAdmin):
    list_display  = ("contract", "user", "assigned_by", "assigned_at")
