from django.db.models import Q
from django.utils import timezone

from academics.models import ClassSubject
from students.models import Guardian

from .models import Announcement


def teacher_class_ids(user):
    return list(
        ClassSubject.objects.filter(teacher=user).values_list("school_class_id", flat=True)
    )


def guardian_class_ids(user):
    return list(
        Guardian.objects.filter(user=user).values_list(
            "student__enrollments__school_class_id", flat=True
        )
    )


def visible_announcements(user):
    """Announcements this account may see, newest first with pinned on top."""
    now = timezone.now()
    current = Announcement.objects.filter(
        Q(expires_at__isnull=True) | Q(expires_at__gte=now)
    ).select_related("school_class", "author")

    if user.is_school_admin or user.is_super_admin:
        return current

    if user.is_teacher:
        class_ids = teacher_class_ids(user)
        return current.filter(
            Q(
                school_class__isnull=True,
                audience__in=[Announcement.Audience.EVERYONE, Announcement.Audience.TEACHERS],
            )
            | Q(school_class_id__in=class_ids)
        )

    if user.is_parent_student:
        class_ids = guardian_class_ids(user)
        return current.filter(
            Q(
                school_class__isnull=True,
                audience__in=[Announcement.Audience.EVERYONE, Announcement.Audience.STUDENTS],
            )
            | Q(school_class_id__in=class_ids)
        )

    return current.none()
