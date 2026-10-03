from django.db import models

from tenancy.models import TenantModel


class EmailLog(TenantModel):
    """A record of an email sent about a student."""

    class Kind(models.TextChoices):
        WELCOME = "welcome", "Student welcome"
        ACCOUNT = "account", "Account welcome"
        GUARDIAN_LINK = "guardian_link", "Guardian linked"
        ENROLLMENT = "enrollment", "Enrollment"
        ABSENCE = "absence", "Absence alert"
        ASSESSMENT = "assessment", "Assessment published"
        RESULTS = "results", "Results"
        DISCIPLINE = "discipline", "Disciplinary notice"

    to_email = models.EmailField()
    subject = models.CharField(max_length=200)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    student = models.ForeignKey(
        "students.Student",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="emails",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        base_manager_name = "objects"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["school", "student", "created_at"], name="emaillog_student_idx")]

    def __str__(self):
        return f"{self.get_kind_display()} to {self.to_email}"
