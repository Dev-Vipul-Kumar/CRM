from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Department


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display  = ("username", "email", "full_name", "role", "status", "department", "is_active")
    list_filter   = ("role", "status", "department")
    search_fields = ("username", "email", "first_name", "last_name")

    fieldsets = UserAdmin.fieldsets + (
        ("CRM Information", {
            "fields": ("role", "status", "phone", "department"),
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("CRM Information", {
            "fields": ("role", "status", "phone", "department"),
        }),
    )


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display  = ("name", "description", "created_at")
    search_fields = ("name",)
