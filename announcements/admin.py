from django.contrib import admin

from core.admin import TenantModelAdmin

from .models import Announcement


@admin.register(Announcement)
class AnnouncementAdmin(TenantModelAdmin):
    list_display = ("title", "audience", "school_class", "author", "is_pinned", "created_at")
    list_filter = ("audience", "is_pinned", "school_class")
    search_fields = ("title", "body")
    list_select_related = ("school_class", "author")
    date_hierarchy = "created_at"
