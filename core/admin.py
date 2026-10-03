from django.contrib import admin, messages

from tenancy.context import get_current_school_id, school_context
from tenancy.models import TenantModel


class TenantModelAdmin(admin.ModelAdmin):
    """Admin for tenant-owned models.

    A Super Admin works across every school: no school has to be selected, records
    from all schools are visible, the owning school is chosen on the form, and
    saves run inside that school's context.

    Any other staff account stays scoped to the active school, picked from
    Platform -> Schools, so tenant data can never leak between schools.
    """

    exclude = ("school",)

    # Optional callable run after a new record is created here, matching the
    # notifications the application screens send. Set as staticmethod(notify_x).
    notify_new = None

    def _unscoped(self, request):
        return request.user.is_superuser

    def get_queryset(self, request):
        if self._unscoped(request):
            return self.model.all_objects.get_queryset()
        return super().get_queryset(request)

    def get_exclude(self, request, obj=None):
        if self._unscoped(request):
            return tuple(field for field in self.exclude if field != "school")
        return self.exclude

    def get_list_filter(self, request):
        filters = list(self.list_filter)
        if self._unscoped(request) and "school" not in filters:
            filters.insert(0, "school")
        return filters

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if self._unscoped(request):
            related = db_field.remote_field.model
            if isinstance(related, type) and issubclass(related, TenantModel):
                kwargs["queryset"] = related.all_objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        # TenantModel.save requires the active school to match the record's school.
        school_id = obj.school_id or get_current_school_id()
        if school_id:
            with school_context(school_id):
                super().save_model(request, obj, form, change)
                self._notify_new(obj, change)
        else:
            super().save_model(request, obj, form, change)
            self._notify_new(obj, change)

    def _notify_new(self, obj, change):
        if change or self.notify_new is None:
            return
        self.notify_new(obj)

    def has_add_permission(self, request):
        if self._unscoped(request):
            return super().has_add_permission(request)
        if get_current_school_id() is None:
            return False
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        if self._unscoped(request):
            return super().has_change_permission(request, obj)
        if get_current_school_id() is None:
            return False
        return super().has_change_permission(request, obj)

    def changelist_view(self, request, extra_context=None):
        if not self._unscoped(request) and get_current_school_id() is None:
            self.message_user(
                request,
                "No school is active, so no records are shown. "
                "Open a school from Platform -> Schools to manage its data.",
                level=messages.WARNING,
            )
        return super().changelist_view(request, extra_context)

    def delete_queryset(self, request, queryset):
        # Deleting does not go through save(), but run it in the record's context
        # anyway so any related cleanup behaves the same way.
        super().delete_queryset(request, queryset)
