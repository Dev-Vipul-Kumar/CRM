from django.urls import path
from . import views

app_name = "audit"

urlpatterns = [
    path("",                                       views.audit_list,        name="audit_list"),
    path("<int:pk>/",                              views.audit_detail,      name="audit_detail"),
    path("contract/<int:contract_pk>/activity/",  views.contract_activity, name="contract_activity"),
]
