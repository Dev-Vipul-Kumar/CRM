from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    path("",           views.reports_index,       name="reports_index"),
    path("export/csv/", views.export_contracts_csv, name="export_csv"),
]
