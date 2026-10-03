from django.test import TestCase
from django.urls import reverse

from academics.models import AcademicTerm, ClassSubject, SchoolClass, Subject
from accounts.models import User
from students.models import Enrollment, Student
from tenancy.context import school_context
from tenancy.models import School


class DashboardTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="North School", slug="north", email="north@example.test")
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
            self.science = Subject.objects.create(name="Science")
            self.mine = SchoolClass.objects.create(name="Grade 6", level=6)
            self.other = SchoolClass.objects.create(name="Grade 7", level=7)
            ClassSubject.objects.create(
                school_class=self.mine, subject=self.science, teacher=self.teacher
            )
            self.student = Student.objects.create(
                admission_number="A-1", first_name="Ada", last_name="Lovelace"
            )
            Enrollment.objects.create(
                student=self.student, school_class=self.mine, term=self.term
            )

    def test_teacher_dashboard_shows_their_teaching(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My teaching")
        self.assertContains(response, "Grade 6")
        self.assertContains(response, "Science")
        self.assertContains(response, "My assessments")

    def test_teacher_class_list_is_scoped(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("dashboard:class_list"))
        self.assertContains(response, "Grade 6")
        self.assertNotContains(response, "Grade 7")

    def test_teacher_cannot_open_a_class_they_do_not_teach(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("dashboard:class_detail", args=[self.other.pk]))
        self.assertEqual(response.status_code, 403)

    def test_teacher_class_detail_shows_the_roster(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("dashboard:class_detail", args=[self.mine.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lovelace")

    def test_admin_dashboard_shows_school_counts(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Students")
        self.assertContains(response, "Teachers")

    def test_parent_is_sent_to_the_portal(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("dashboard:home"))
        self.assertRedirects(response, reverse("portal:home"))
