from django.db import IntegrityError, transaction
from django.test import TestCase

from academics.models import AcademicTerm
from students.models import Student
from tenancy.context import school_context
from tenancy.models import School

from .models import AttendanceRecord


class AttendanceIsolationTests(TestCase):
    def setUp(self):
        self.school_a = School.objects.create(name="North School", slug="north", email="north@example.test")
        self.school_b = School.objects.create(name="South School", slug="south", email="south@example.test")

    def _student(self, number="A-1"):
        return Student.objects.create(admission_number=number, first_name="Ada", last_name="Lovelace")

    def test_attendance_is_scoped_and_unique_per_day(self):
        with school_context(self.school_a):
            term = AcademicTerm.objects.create(
                name="Term 1", start_date="2026-01-10", end_date="2026-04-10", is_current=True
            )
            student = self._student()
            AttendanceRecord.objects.create(
                student=student, term=term, date="2026-02-03", status=AttendanceRecord.Status.PRESENT
            )
            self.assertEqual(AttendanceRecord.objects.count(), 1)

            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    AttendanceRecord.objects.create(
                        student=student, term=term, date="2026-02-03", status=AttendanceRecord.Status.ABSENT
                    )

        with school_context(self.school_b):
            self.assertEqual(AttendanceRecord.objects.count(), 0)
