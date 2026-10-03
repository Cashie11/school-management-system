from django.contrib import admin

from .models import SupportMessage


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "email", "school", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "email", "subject", "body")
    list_select_related = ("school",)
    date_hierarchy = "created_at"
    readonly_fields = ("name", "email", "school", "subject", "body", "created_at")
