from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from tenancy.context import school_context
from tenancy.models import School

from .models import AcademicTerm, Subject


class AcademicsViewTests(TestCase):
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
        self.other_teacher = User.objects.create_user(
            email="teacher@south.example.test",
            password="a-strong-test-password",
            school=self.other,
            role=User.Role.TEACHER,
        )

    def test_requires_login(self):
        response = self.client.get(reverse("academics:term_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_teacher_cannot_manage_academics(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("academics:term_list"))
        self.assertEqual(response.status_code, 403)

    def test_admin_creates_term_in_own_school(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("academics:term_create"),
            {"name": "Term 1", "start_date": "2026-01-10", "end_date": "2026-04-10", "is_current": "on"},
        )
        self.assertRedirects(response, reverse("academics:term_list"))
        with school_context(self.school):
            term = AcademicTerm.objects.get()
        self.assertEqual(term.school, self.school)
        self.assertTrue(term.is_current)

    def test_cross_tenant_object_returns_404(self):
        with school_context(self.other):
            subject = Subject.objects.create(name="Chemistry")
        self.client.force_login(self.admin)
        response = self.client.get(reverse("academics:subject_edit", args=[subject.pk]))
        self.assertEqual(response.status_code, 404)

    def test_teacher_dropdown_is_scoped_to_the_school(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("academics:assignment_create"))
        self.assertContains(response, "teacher@north.example.test")
        self.assertNotContains(response, "teacher@south.example.test")

    def test_subject_list_only_shows_own_school(self):
        with school_context(self.school):
            Subject.objects.create(name="Mathematics")
        with school_context(self.other):
            Subject.objects.create(name="Chemistry")
        self.client.force_login(self.admin)
        response = self.client.get(reverse("academics:subject_list"))
        self.assertContains(response, "Mathematics")
        self.assertNotContains(response, "Chemistry")
