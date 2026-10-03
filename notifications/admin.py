from django.contrib import admin

from core.admin import TenantModelAdmin

from .models import EmailLog


@admin.register(EmailLog)
class EmailLogAdmin(TenantModelAdmin):
    list_display = ("created_at", "kind", "to_email", "subject", "student")
    list_filter = ("kind",)
    search_fields = ("to_email", "subject")
    list_select_related = ("student",)
    date_hierarchy = "created_at"
    readonly_fields = ("to_email", "subject", "kind", "student", "created_at")
