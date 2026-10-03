from django.conf import settings
from django.db import models

from tenancy.models import TenantModel


class AcademicTerm(TenantModel):
    name = models.CharField(max_length=80)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        base_manager_name = "objects"
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="uniq_term_name_per_school"),
            models.UniqueConstraint(
                fields=["school"],
                condition=models.Q(is_current=True),
                name="uniq_current_term_per_school",
            ),
        ]

    def __str__(self):
        return self.name


class Subject(TenantModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20, blank=True)

    class Meta:
        base_manager_name = "objects"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="uniq_subject_name_per_school")
        ]

    def __str__(self):
        return self.name


class SchoolClass(TenantModel):
    name = models.CharField(max_length=120)
    level = models.PositiveSmallIntegerField()

    class Meta:
        base_manager_name = "objects"
        ordering = ["level", "name"]
        constraints = [
            models.UniqueConstraint(fields=["school", "level", "name"], name="uniq_class_per_school")
        ]

    def __str__(self):
        return self.name


class ClassSubject(TenantModel):
    """A subject taught to a class, optionally assigned to a teacher."""

    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name="class_subjects")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="class_subjects")
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="class_subjects",
    )

    class Meta:
        base_manager_name = "objects"
        ordering = ["school_class__level", "school_class__name", "subject__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "school_class", "subject"], name="uniq_class_subject_per_school"
            )
        ]

    def __str__(self):
        return f"{self.school_class} - {self.subject}"
