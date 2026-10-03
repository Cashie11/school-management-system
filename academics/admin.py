from django.contrib import admin

from core.admin import TenantModelAdmin

from .models import AcademicTerm, ClassSubject, SchoolClass, Subject


@admin.register(AcademicTerm)
class AcademicTermAdmin(TenantModelAdmin):
    list_display = ("name", "start_date", "end_date", "is_current")
    list_filter = ("is_current",)


@admin.register(Subject)
class SubjectAdmin(TenantModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")


@admin.register(SchoolClass)
class SchoolClassAdmin(TenantModelAdmin):
    list_display = ("name", "level")
    list_filter = ("level",)


@admin.register(ClassSubject)
class ClassSubjectAdmin(TenantModelAdmin):
    list_display = ("school_class", "subject", "teacher")
    list_filter = ("school_class", "subject")
    list_select_related = ("school_class", "subject", "teacher")
