from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("",                          views.notification_list,   name="notification_list"),
    path("<int:pk>/read/",            views.mark_read,           name="mark_read"),
    path("<int:pk>/archive/",         views.archive_notification, name="archive_notification"),
    path("mark-all-read/",            views.mark_all_read,       name="mark_all_read"),
]
