from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from academics.models import AcademicTerm, ClassSubject, SchoolClass, Subject
from accounts.models import User
from students.models import Enrollment, Student
from tenancy.context import school_context
from tenancy.models import School

from .models import Assessment, Score


class ResultsViewTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="North School", slug="north", email="north@example.test")
        self.other = School.objects.create(name="South School", slug="south", email="south@example.test")
        self.admin = User.objects.create_user(
            email="admin@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.SCHOOL_ADMIN,
        )
        self.teacher = User.objects.create_user(
            email="teacher@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.TEACHER,
        )
        with school_context(self.school):
            self.term = AcademicTerm.objects.create(
                name="Term 1", start_date="2026-01-10", end_date="2026-04-10", is_current=True
            )
            self.school_class = SchoolClass.objects.create(name="Grade 6", level=6)
            self.subject = Subject.objects.create(name="Mathematics")
            self.class_subject = ClassSubject.objects.create(
                school_class=self.school_class, subject=self.subject, teacher=self.teacher
            )
            self.student = Student.objects.create(
                admission_number="A-1", first_name="Ada", last_name="Lovelace"
            )
            Enrollment.objects.create(
                student=self.student, school_class=self.school_class, term=self.term
            )
            self.assessment = Assessment.objects.create(
                class_subject=self.class_subject, term=self.term, name="Midterm", max_score=50
            )

    def test_teacher_enters_scores(self):
        self.client.force_login(self.teacher)
        response = self.client.post(
            reverse("results:score_entry", args=[self.assessment.pk]),
            {f"value_{self.student.pk}": "40"},
        )
        self.assertEqual(response.status_code, 302)
        with school_context(self.school):
            self.assertEqual(Score.objects.get().value, Decimal("40.00"))

    def test_score_out_of_range_is_rejected(self):
        self.client.force_login(self.teacher)
        response = self.client.post(
            reverse("results:score_entry", args=[self.assessment.pk]),
            {f"value_{self.student.pk}": "80"},
        )
        self.assertEqual(response.status_code, 200)
        with school_context(self.school):
            self.assertEqual(Score.objects.count(), 0)

    def test_teacher_cannot_open_another_teachers_assessment(self):
        other_teacher = User.objects.create_user(
            email="teacher2@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.TEACHER,
        )
        self.client.force_login(other_teacher)
        response = self.client.get(reverse("results:score_entry", args=[self.assessment.pk]))
        self.assertEqual(response.status_code, 403)

    def test_cross_tenant_assessment_returns_404(self):
        with school_context(self.other):
            other_class = SchoolClass.objects.create(name="Grade 9", level=9)
            other_subject = Subject.objects.create(name="Physics")
            other_class_subject = ClassSubject.objects.create(
                school_class=other_class, subject=other_subject
            )
            other_term = AcademicTerm.objects.create(
                name="Term 1", start_date="2026-01-10", end_date="2026-04-10"
            )
            other_assessment = Assessment.objects.create(
                class_subject=other_class_subject, term=other_term, name="Exam", max_score=100
            )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("results:score_entry", args=[other_assessment.pk]))
        self.assertEqual(response.status_code, 404)

    def test_report_card_aggregates_and_downloads_pdf(self):
        with school_context(self.school):
            Score.objects.create(
                assessment=self.assessment, student=self.student, value=Decimal("40")
            )
        self.client.force_login(self.admin)
        page = self.client.get(
            reverse("results:report_card", args=[self.student.pk, self.term.pk])
        )
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "80.00%")

        pdf = self.client.get(
            reverse("results:report_card_download", args=[self.student.pk, self.term.pk])
        )
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))

    def test_duplicate_assessment_name_is_a_form_error(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("results:assessment_create"),
            {
                "class_subject": self.class_subject.pk,
                "term": self.term.pk,
                "name": "Midterm",
                "mode": Assessment.Mode.MANUAL,
                "max_score": "50",
            },
        )
        # A duplicate is reported on the form, not as a server error.
        self.assertEqual(response.status_code, 200)
        with school_context(self.school):
            self.assertEqual(Assessment.objects.count(), 1)

    def test_assessment_window_must_be_ordered(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("results:assessment_create"),
            {
                "class_subject": self.class_subject.pk,
                "term": self.term.pk,
                "name": "Window test",
                "mode": Assessment.Mode.ONLINE,
                "max_score": "10",
                "available_from": "2026-03-01T10:00",
                "available_until": "2026-03-01T09:00",
            },
        )
        self.assertEqual(response.status_code, 200)
        with school_context(self.school):
            self.assertFalse(Assessment.objects.filter(name="Window test").exists())

    def test_parent_cannot_access_results(self):
        parent = User.objects.create_user(
            email="parent@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.PARENT_STUDENT,
        )
        self.client.force_login(parent)
        self.assertEqual(self.client.get(reverse("results:assessment_list")).status_code, 403)
