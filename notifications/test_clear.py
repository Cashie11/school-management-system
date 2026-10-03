from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from students.models import Student
from tenancy.context import school_context
from tenancy.models import School

from .models import EmailLog


class ClearNotificationsTests(TestCase):
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
            self.student = Student.objects.create(
                admission_number="A-1", first_name="Ada", last_name="Lovelace"
            )
            self.other_student = Student.objects.create(
                admission_number="A-2", first_name="Grace", last_name="Hopper"
            )
            for index in range(3):
                EmailLog.objects.create(
                    kind=EmailLog.Kind.WELCOME,
                    to_email=f"ada{index}@example.test",
                    subject="Welcome",
                    student=self.student,
                )
            EmailLog.objects.create(
                kind=EmailLog.Kind.WELCOME,
                to_email="grace@example.test",
                subject="Welcome",
                student=self.other_student,
            )

    def test_the_confirmation_page_reports_the_count(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("notifications:clear_student_emails", args=[self.student.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "recorded notifications")
        self.assertContains(response, "<strong>3</strong>")

    def test_clearing_removes_only_that_students_history(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("notifications:clear_student_emails", args=[self.student.pk])
        )
        self.assertRedirects(
            response, reverse("students:student_detail", args=[self.student.pk])
        )
        with school_context(self.school):
            self.assertEqual(EmailLog.objects.filter(student=self.student).count(), 0)
            self.assertEqual(EmailLog.objects.filter(student=self.other_student).count(), 1)

    def test_the_clear_action_is_a_post(self):
        self.client.force_login(self.admin)
        self.client.get(reverse("notifications:clear_student_emails", args=[self.student.pk]))
        with school_context(self.school):
            self.assertEqual(EmailLog.objects.filter(student=self.student).count(), 3)

    def test_a_teacher_cannot_clear_notifications(self):
        self.client.force_login(self.teacher)
        response = self.client.post(
            reverse("notifications:clear_student_emails", args=[self.student.pk])
        )
        self.assertEqual(response.status_code, 403)
        with school_context(self.school):
            self.assertEqual(EmailLog.objects.filter(student=self.student).count(), 3)

    def test_another_schools_student_is_not_reachable(self):
        with school_context(self.other):
            stranger = Student.objects.create(
                admission_number="B-1", first_name="Alan", last_name="Turing"
            )
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("notifications:clear_student_emails", args=[stranger.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_the_student_page_offers_the_clear_action(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("students:student_detail", args=[self.student.pk]))
        self.assertContains(response, "Clear all")
