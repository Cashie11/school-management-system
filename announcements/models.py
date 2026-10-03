from django.conf import settings
from django.db import models
from django.utils import timezone

from tenancy.models import TenantModel


class Announcement(TenantModel):
    """A notice shown to part of a school.

    The audience decides who sees it. A class announcement is addressed to the
    families of that class, and the teachers of that class see it too.
    """

    class Audience(models.TextChoices):
        EVERYONE = "everyone", "Everyone"
        TEACHERS = "teachers", "Teachers"
        STUDENTS = "students", "Parents and Students"

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="announcements",
    )
    audience = models.CharField(max_length=12, choices=Audience.choices, default=Audience.EVERYONE)
    school_class = models.ForeignKey(
        "academics.SchoolClass",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="announcements",
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_pinned = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        base_manager_name = "objects"
        ordering = ["-is_pinned", "-created_at"]
        indexes = [models.Index(fields=["school", "audience"], name="ann_school_audience_idx")]

    @property
    def is_expired(self):
        return self.expires_at is not None and self.expires_at <= timezone.now()

    def __str__(self):
        return self.title
