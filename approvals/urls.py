from django.urls import path
from . import views

app_name = "approvals"

urlpatterns = [
    path("",                                       views.approval_list,    name="approval_list"),
    path("<int:pk>/",                              views.approval_detail,  name="approval_detail"),
    path("contract/<int:contract_pk>/submit/",    views.submit_for_review, name="submit_for_review"),
    path("contract/<int:contract_pk>/action/",    views.approval_action,  name="approval_action"),
]
