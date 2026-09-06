from django.contrib import admin
from .models import Signature


@admin.register(Signature)
class SignatureAdmin(admin.ModelAdmin):
    list_display  = ("contract", "signer", "status", "requested_at", "signed_at")
    list_filter   = ("status",)
    search_fields = ("contract__contract_number", "signer__username")
