from django.urls import path
from . import views
from . import admin_portal_views as apv

app_name = "accounts"

urlpatterns = [
    # ── Public ──────────────────────────────────────────────
    path("",        views.landing,     name="landing"),
    path("login/",  views.login_view,  name="login"),
    path("logout/", views.logout_view, name="logout"),

    # ── Admin Portal ─────────────────────────────────────────
    path("admin-portal/",                           apv.admin_portal,           name="admin_portal"),

    # Portal — user management
    path("admin-portal/users/create/",              apv.portal_user_create,     name="portal_user_create"),
    path("admin-portal/users/<int:pk>/edit/",       apv.portal_user_edit,       name="portal_user_edit"),
    path("admin-portal/users/<int:pk>/toggle/",     apv.portal_user_toggle,     name="portal_user_toggle"),
    path("admin-portal/users/<int:pk>/delete/",     apv.portal_user_delete,     name="portal_user_delete"),
    path("admin-portal/users/<int:pk>/password/",   apv.portal_reset_password,  name="portal_reset_password"),
    path("admin-portal/users/<int:pk>/role/",       apv.portal_user_role_change,name="portal_user_role_change"),

    # Portal — department management
    path("admin-portal/departments/create/",        apv.portal_dept_create,     name="portal_dept_create"),
    path("admin-portal/departments/<int:pk>/edit/", apv.portal_dept_edit,       name="portal_dept_edit"),
    path("admin-portal/departments/<int:pk>/delete/",apv.portal_dept_delete,    name="portal_dept_delete"),

    # ── Standard CRM views (sidebar) ────────────────────────
    path("users/",                          views.user_list,           name="user_list"),
    path("users/create/",                   views.user_create,         name="user_create"),
    path("users/<int:pk>/",                 views.user_detail,         name="user_detail"),
    path("users/<int:pk>/edit/",            views.user_edit,           name="user_edit"),
    path("users/<int:pk>/reset-password/",  views.user_reset_password, name="user_reset_password"),
    path("users/<int:pk>/toggle-status/",   views.user_toggle_status,  name="user_toggle_status"),

    # Departments
    path("departments/",                    views.department_list,   name="department_list"),
    path("departments/create/",             views.department_create, name="department_create"),
    path("departments/<int:pk>/edit/",      views.department_edit,   name="department_edit"),
    path("departments/<int:pk>/delete/",    views.department_delete, name="department_delete"),
]
