from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path("admin/",          admin.site.urls),
    path("",                include("accounts.urls",      namespace="accounts")),
    path("dashboard/",      include("dashboard.urls",     namespace="dashboard")),
    path("contracts/",      include("contracts.urls",     namespace="contracts")),
    path("approvals/",      include("approvals.urls",     namespace="approvals")),
    path("signatures/",     include("signatures.urls",    namespace="signatures")),
    path("notifications/",  include("notifications.urls", namespace="notifications")),
    path("audit/",          include("audit.urls",         namespace="audit")),
    path("reports/",        include("reports.urls",       namespace="reports")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
