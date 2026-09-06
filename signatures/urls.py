from django.urls import path
from . import views

app_name = "signatures"

urlpatterns = [
    path("",                                            views.signature_list,    name="signature_list"),
    path("<int:pk>/",                                   views.signature_detail,  name="signature_detail"),
    path("<int:signature_pk>/sign/",                    views.sign_contract,     name="sign_contract"),
    path("contract/<int:contract_pk>/request/",         views.request_signature, name="request_signature"),
]
