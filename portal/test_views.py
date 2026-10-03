from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from academics.models import AcademicTerm, ClassSubject, SchoolClass, Subject
from accounts.models import User
from attendance.models import AttendanceRecord
from results.models import Assessment, Score
from students.models import Enrollment, Guardian, Student
from tenancy.context import school_context
from tenancy.models import School


class PortalResultsTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="North School", slug="north", email="north@example.test")
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
            class_subject = ClassSubject.objects.create(
                school_class=self.school_class, subject=self.subject
            )
            self.student = Student.objects.create(
                admission_number="A-1", first_name="Ada", last_name="Lovelace"
            )
            Enrollment.objects.create(
                student=self.student, school_class=self.school_class, term=self.term
            )
            Guardian.objects.create(user=self.parent, student=self.student, is_primary=True)
            assessment = Assessment.objects.create(
                class_subject=class_subject, term=self.term, name="Midterm", max_score=50
            )
            Score.objects.create(assessment=assessment, student=self.student, value=Decimal("40"))
            AttendanceRecord.objects.create(
                student=self.student,
                term=self.term,
                date="2026-02-03",
                status=AttendanceRecord.Status.PRESENT,
            )

    def test_parent_sees_the_report_card(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("portal:student_results", args=[self.student.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lovelace")
        self.assertContains(response, "80.00%")
        self.assertContains(response, "Mathematics")

    def test_parent_downloads_the_report_pdf(self):
        self.client.force_login(self.parent)
        response = self.client.get(
            reverse("portal:student_report_pdf", args=[self.student.pk, self.term.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_parent_sees_attendance(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("portal:student_attendance", args=[self.student.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Present")
        self.assertContains(response, "3 Feb 2026")

    def test_parent_cannot_view_another_familys_student(self):
        with school_context(self.school):
            stranger = Student.objects.create(
                admission_number="A-9", first_name="Alan", last_name="Turing"
            )
        self.client.force_login(self.parent)
        self.assertEqual(
            self.client.get(reverse("portal:student_results", args=[stranger.pk])).status_code, 404
        )
        self.assertEqual(
            self.client.get(reverse("portal:student_attendance", args=[stranger.pk])).status_code,
            404,
        )

    def test_staff_cannot_use_the_portal(self):
        teacher = User.objects.create_user(
            email="teacher@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.TEACHER,
        )
        self.client.force_login(teacher)
        self.assertEqual(self.client.get(reverse("portal:home")).status_code, 403)
