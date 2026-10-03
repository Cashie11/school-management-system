from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from core.crud import delete_view, form_view
from core.permissions import member_required, teaching_required

from .forms import AnnouncementForm
from .models import Announcement
from .selectors import teacher_class_ids, visible_announcements


def _may_manage(user, announcement):
    if user.is_school_admin or user.is_super_admin:
        return True
    return (
        user.is_teacher
        and announcement.author_id == user.pk
        and announcement.school_class_id in teacher_class_ids(user)
    )


def _managed_or_403(user, announcement):
    if not _may_manage(user, announcement):
        raise PermissionDenied("You can only change announcements you created for your own classes.")
    return announcement


@member_required
def announcement_list(request):
    return render(
        request,
        "announcements/list.html",
        {
            "announcements": visible_announcements(request.user),
            "can_create": not request.user.is_parent_student,
        },
    )


@teaching_required
def announcement_create(request):
    def set_author(announcement):
        announcement.author = request.user
        announcement.save(update_fields=["author"])

    return form_view(
        request,
        form_class=AnnouncementForm,
        template="announcements/form.html",
        title="New announcement",
        success_url="announcements:list",
        save_message="Announcement published.",
        form_kwargs={"user": request.user},
        on_save=set_author,
        extra={"cancel_url": reverse("announcements:list"), "full_fields": ["title"]},
    )


@teaching_required
def announcement_edit(request, pk):
    announcement = _managed_or_403(request.user, get_object_or_404(Announcement, pk=pk))
    return form_view(
        request,
        form_class=AnnouncementForm,
        template="announcements/form.html",
        title="Edit announcement",
        instance=announcement,
        success_url="announcements:list",
        save_message="Announcement saved.",
        form_kwargs={"user": request.user},
        extra={"cancel_url": reverse("announcements:list"), "full_fields": ["title"]},
    )


@teaching_required
def announcement_delete(request, pk):
    announcement = _managed_or_403(request.user, get_object_or_404(Announcement, pk=pk))
    return delete_view(
        request,
        obj=announcement,
        template="partials/_confirm_delete.html",
        success_url="announcements:list",
        success_message="Announcement deleted.",
        extra={"cancel_url": reverse("announcements:list")},
    )
