from django.test import TestCase

from academics.models import AcademicTerm, SchoolClass
from accounts.models import User
from tenancy.context import school_context
from tenancy.models import School

from .models import Enrollment, Guardian, Student


class StudentIsolationTests(TestCase):
    def setUp(self):
        self.school_a = School.objects.create(name="North School", slug="north", email="north@example.test")
        self.school_b = School.objects.create(name="South School", slug="south", email="south@example.test")

    def test_students_are_scoped_to_the_active_school(self):
        with school_context(self.school_a):
            Student.objects.create(admission_number="A-1", first_name="Ada", last_name="Lovelace")

        with school_context(self.school_b):
            self.assertEqual(Student.objects.count(), 0)
            Student.objects.create(admission_number="B-1", first_name="Alan", last_name="Turing")

        with school_context(self.school_a):
            self.assertEqual(list(Student.objects.values_list("admission_number", flat=True)), ["A-1"])

    def test_admission_numbers_are_unique_per_school(self):
        with school_context(self.school_a):
            Student.objects.create(admission_number="A-1", first_name="Ada", last_name="Lovelace")
        with school_context(self.school_b):
            # Same admission number is fine in another school.
            Student.objects.create(admission_number="A-1", first_name="Alan", last_name="Turing")
            self.assertEqual(Student.objects.count(), 1)

    def test_enrollment_keeps_history_and_is_scoped(self):
        with school_context(self.school_a):
            term = AcademicTerm.objects.create(
                name="Term 1", start_date="2026-01-10", end_date="2026-04-10", is_current=True
            )
            school_class = SchoolClass.objects.create(name="Grade 6", level=6)
            student = Student.objects.create(
                admission_number="A-1", first_name="Ada", last_name="Lovelace"
            )
            Enrollment.objects.create(student=student, school_class=school_class, term=term)

            self.assertEqual(student.enrollments.count(), 1)
            self.assertEqual(school_class.enrollments.count(), 1)

        with school_context(self.school_b):
            self.assertEqual(Enrollment.objects.count(), 0)

    def test_guardian_links_account_to_students(self):
        with school_context(self.school_a):
            first = Student.objects.create(admission_number="A-1", first_name="Ada", last_name="Lovelace")
            second = Student.objects.create(admission_number="A-2", first_name="Grace", last_name="Hopper")

        parent = User.objects.create_user(
            email="parent@north.example.test",
            password="a-strong-test-password",
            school=self.school_a,
            role=User.Role.PARENT_STUDENT,
        )
        with school_context(self.school_a):
            Guardian.objects.create(user=parent, student=first, relationship="Mother", is_primary=True)
            Guardian.objects.create(user=parent, student=second, relationship="Mother", is_primary=True)
            self.assertEqual(parent.guardianships.count(), 2)
