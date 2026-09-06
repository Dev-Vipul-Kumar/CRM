from django.urls import path
from . import views

app_name = "contracts"

urlpatterns = [
    # Contracts
    path("",                              views.contract_list,           name="contract_list"),
    path("create/",                       views.contract_create,         name="contract_create"),
    path("<int:pk>/",                     views.contract_detail,         name="contract_detail"),
    path("<int:pk>/edit/",                views.contract_edit,           name="contract_edit"),
    path("<int:pk>/versions/",            views.contract_versions,       name="contract_versions"),
    path("<int:pk>/upload-version/",      views.contract_upload_version, name="contract_upload_version"),
    path("<int:pk>/assign/",              views.contract_assign,         name="contract_assign"),
    path("<int:pk>/archive/",             views.contract_archive,        name="contract_archive"),
    path("<int:pk>/renew/",               views.contract_renew,          name="contract_renew"),
    path("<int:pk>/cancel/",              views.contract_cancel,         name="contract_cancel"),

    # Document download
    path("version/<int:version_pk>/download/", views.download_document, name="download_document"),

    # Categories
    path("categories/",                   views.category_list,   name="category_list"),
    path("categories/create/",            views.category_create, name="category_create"),
    path("categories/<int:pk>/edit/",     views.category_edit,   name="category_edit"),
    path("categories/<int:pk>/delete/",   views.category_delete, name="category_delete"),
]
