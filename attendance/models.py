from django.conf import settings
from django.db import models

from tenancy.models import TenantModel


class AttendanceRecord(TenantModel):
    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        LATE = "late", "Late"
        EXCUSED = "excused", "Excused"

    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="attendance_records"
    )
    term = models.ForeignKey(
        "academics.AcademicTerm", on_delete=models.CASCADE, related_name="attendance_records"
    )
    date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PRESENT)
    note = models.CharField(max_length=200, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recorded_attendance",
    )

    class Meta:
        base_manager_name = "objects"
        ordering = ["-date", "student__last_name", "student__first_name"]
        constraints = [
            models.UniqueConstraint(fields=["school", "student", "date"], name="uniq_attendance_per_day")
        ]
        indexes = [models.Index(fields=["school", "date"], name="attendance_school_date_idx")]

    def __str__(self):
        return f"{self.student} {self.date} {self.get_status_display()}"
