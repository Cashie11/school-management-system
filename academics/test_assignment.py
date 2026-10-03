from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from tenancy.context import school_context
from tenancy.models import School

from .models import ClassSubject, SchoolClass, Subject


class AssignmentCreationTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="North School", slug="north", email="north@example.test")
        self.admin = User.objects.create_user(
            email="admin@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.SCHOOL_ADMIN,
        )
        with school_context(self.school):
            self.subject = Subject.objects.create(name="Mathematics")
            self.school_class = SchoolClass.objects.create(name="Grade 7", level=7)
        self.teacher = User.objects.create_user(
            email="teacher@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.TEACHER,
        )

    def test_form_renders_the_available_options(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("academics:assignment_create"))
        self.assertContains(response, "Grade 7")
        self.assertContains(response, "Mathematics")
        self.assertContains(response, "teacher@north.example.test")

    def test_creates_assignment(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("academics:assignment_create"),
            {
                "school_class": self.school_class.pk,
                "subject": self.subject.pk,
                "teacher": self.teacher.pk,
            },
        )
        self.assertRedirects(response, reverse("academics:assignment_list"))
        with school_context(self.school):
            assignment = ClassSubject.objects.get()
            self.assertEqual(assignment.teacher, self.teacher)
            self.assertEqual(assignment.school_class, self.school_class)
