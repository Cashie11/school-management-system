from django.contrib import admin

from core.admin import TenantModelAdmin
from notifications.services import (
    notify_discipline,
    notify_enrollment,
    notify_guardian_linked,
    notify_student_welcome,
)

from .models import DisciplineRecord, Enrollment, Guardian, Student


@admin.register(Student)
class StudentAdmin(TenantModelAdmin):
    list_display = ("full_name", "admission_number", "email", "gender", "is_active")
    list_filter = ("is_active", "gender")
    search_fields = ("first_name", "last_name", "admission_number", "email")
    notify_new = staticmethod(notify_student_welcome)


@admin.register(Enrollment)
class EnrollmentAdmin(TenantModelAdmin):
    list_display = ("student", "school_class", "term")
    list_filter = ("school_class", "term")
    list_select_related = ("student", "school_class", "term")
    notify_new = staticmethod(notify_enrollment)


@admin.register(Guardian)
class GuardianAdmin(TenantModelAdmin):
    list_display = ("user", "student", "relationship", "is_primary")
    list_filter = ("relationship", "is_primary")
    list_select_related = ("user", "student")
    notify_new = staticmethod(notify_guardian_linked)


@admin.register(DisciplineRecord)
class DisciplineRecordAdmin(TenantModelAdmin):
    list_display = ("student", "kind", "start_date", "end_date", "issued_by", "created_at")
    list_filter = ("kind",)
    list_select_related = ("student", "issued_by")
    notify_new = staticmethod(notify_discipline)

    def save_model(self, request, obj, form, change):
        if not obj.issued_by_id:
            obj.issued_by = request.user
        super().save_model(request, obj, form, change)
