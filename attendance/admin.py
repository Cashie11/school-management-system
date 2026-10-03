from django.contrib import admin

from core.admin import TenantModelAdmin
from notifications.services import notify_absence

from .models import AttendanceRecord


def _notify_attendance(record):
    if record.status == AttendanceRecord.Status.ABSENT:
        notify_absence(record)


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(TenantModelAdmin):
    list_display = ("student", "date", "status", "term")
    list_filter = ("status", "term", "date")
    search_fields = ("student__first_name", "student__last_name")
    date_hierarchy = "date"
    list_select_related = ("student", "term")
    notify_new = staticmethod(_notify_attendance)
