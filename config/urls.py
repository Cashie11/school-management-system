from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", health, name="health"),
    path("health/", health),
    path("", include("core.urls")),
    path("accounts/", include("accounts.urls")),
    path("academics/", include("academics.urls")),
    path("students/", include("students.urls")),
    path("attendance/", include("attendance.urls")),
    path("results/", include("results.urls")),
    path("portal/", include("portal.urls")),
    path("notifications/", include("notifications.urls")),
    path("announcements/", include("announcements.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("platform/", include("tenancy.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
