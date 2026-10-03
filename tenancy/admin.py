from django.contrib import admin
from django.utils.html import format_html

from .models import School


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("logo_preview", "name", "slug", "email", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "email")
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Logo")
    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" alt="" style="height:32px;border-radius:6px;">', obj.logo.url
            )
        return "-"
