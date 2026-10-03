from django.conf import settings
from django.db import models

from tenancy.models import TenantModel


class Student(TenantModel):
    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"

    admission_number = models.CharField(max_length=40)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    email = models.EmailField(blank=True, help_text="Optional. Notification mail falls back to linked guardians.")
    is_active = models.BooleanField(default=True)

    class Meta:
        base_manager_name = "objects"
        ordering = ["last_name", "first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "admission_number"], name="uniq_admission_number_per_school"
            )
        ]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return f"{self.full_name} ({self.admission_number})"


class Enrollment(TenantModel):
    """A student's placement in a class for a term. Kept as history."""

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="enrollments")
    school_class = models.ForeignKey(
        "academics.SchoolClass", on_delete=models.CASCADE, related_name="enrollments"
    )
    term = models.ForeignKey(
        "academics.AcademicTerm", on_delete=models.CASCADE, related_name="enrollments"
    )

    class Meta:
        base_manager_name = "objects"
        ordering = ["student__last_name", "student__first_name"]
        constraints = [
            models.UniqueConstraint(fields=["school", "student", "term"], name="uniq_enrollment_per_term")
        ]
        indexes = [models.Index(fields=["school", "school_class", "term"], name="enroll_class_term_idx")]

    def __str__(self):
        return f"{self.student} in {self.school_class} ({self.term})"


class Guardian(TenantModel):
    """Links a Parent/Student account to a student record it may view."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="guardianships"
    )
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="guardians")
    relationship = models.CharField(max_length=40, blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        base_manager_name = "objects"
        ordering = ["student__last_name", "student__first_name"]
        constraints = [
            models.UniqueConstraint(fields=["school", "user", "student"], name="uniq_guardian_link")
        ]

    def __str__(self):
        return f"{self.user} -> {self.student}"


class DisciplineRecord(TenantModel):
    """A sanction recorded against a student. Guardians are notified by email."""

    class Kind(models.TextChoices):
        WARNING = "warning", "Warning"
        SUSPENSION = "suspension", "Suspension"
        EXPULSION = "expulsion", "Expulsion"

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="discipline_records")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    reason = models.TextField()
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="issued_discipline",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        base_manager_name = "objects"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_kind_display()} for {self.student}"

    @property
    def is_permanent(self):
        return self.kind == self.Kind.EXPULSION
