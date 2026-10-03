from django.test import TestCase
from django.urls import reverse

from academics.models import AcademicTerm, ClassSubject, SchoolClass, Subject
from accounts.models import User
from students.models import Enrollment, Guardian, Student
from tenancy.context import school_context
from tenancy.models import School


class UntrustedInputTests(TestCase):
    """Non-numeric query values must never reach a numeric filter."""

    def setUp(self):
        self.school = School.objects.create(name="North School", slug="north", email="north@example.test")
        self.admin = User.objects.create_user(
            email="admin@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.SCHOOL_ADMIN,
        )
        self.parent = User.objects.create_user(
            email="parent@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.PARENT_STUDENT,
        )
        with school_context(self.school):
            self.term = AcademicTerm.objects.create(
                name="Term 1", start_date="2026-01-10", end_date="2026-04-10", is_current=True
            )
            self.school_class = SchoolClass.objects.create(name="Grade 6", level=6)
            self.subject = Subject.objects.create(name="Mathematics")
            ClassSubject.objects.create(
                school_class=self.school_class, subject=self.subject, teacher=self.admin
            )
            self.student = Student.objects.create(
                admission_number="A-1", first_name="Ada", last_name="Lovelace"
            )
            Enrollment.objects.create(
                student=self.student, school_class=self.school_class, term=self.term
            )
            Guardian.objects.create(user=self.parent, student=self.student)

    def test_attendance_register_tolerates_junk_parameters(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("attendance:register"),
            {"school_class": "abc", "term": "nope", "date": "not-a-date"},
        )
        self.assertEqual(response.status_code, 200)

    def test_attendance_records_tolerate_a_junk_class(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("attendance:record_list"), {"school_class": "abc"}
        )
        self.assertEqual(response.status_code, 200)

    def test_attendance_enroll_ignores_a_junk_student(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("attendance:register"),
            {
                "action": "enroll",
                "student": "abc",
                "school_class": self.school_class.pk,
                "term": self.term.pk,
            },
        )
        self.assertEqual(response.status_code, 302)

    def test_report_card_select_tolerates_a_junk_term(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("results:report_card_select"), {"term": "abc"})
        self.assertEqual(response.status_code, 200)

    def test_portal_attendance_tolerates_a_junk_term(self):
        self.client.force_login(self.parent)
        response = self.client.get(
            reverse("portal:student_attendance", args=[self.student.pk]), {"term": "abc"}
        )
        self.assertEqual(response.status_code, 200)
