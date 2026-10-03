from django.test import TestCase
from django.urls import reverse

from students.models import Guardian, Student
from tenancy.context import school_context
from tenancy.models import School

from .models import User


class StaffAccountTests(TestCase):
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

    def test_teacher_cannot_reach_account_pages(self):
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(reverse("accounts:staff_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("accounts:parent_list")).status_code, 403)

    def test_admin_creates_a_teacher(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("accounts:staff_create"),
            {
                "first_name": "Grace",
                "last_name": "Hopper",
                "email": "grace@north.example.test",
                "role": User.Role.TEACHER,
                "password1": "a-strong-test-password",
                "password2": "a-strong-test-password",
            },
        )
        self.assertRedirects(response, reverse("accounts:staff_list"))
        created = User.objects.get(email="grace@north.example.test")
        self.assertEqual(created.school, self.school)
        self.assertEqual(created.role, User.Role.TEACHER)

    def test_staff_form_does_not_offer_parent_role(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("accounts:staff_create"))
        self.assertNotContains(response, "Parent/Student")

    def test_staff_list_only_shows_own_school(self):
        User.objects.create_user(
            email="outsider@south.example.test",
            password="a-strong-test-password",
            school=self.other,
            role=User.Role.TEACHER,
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("accounts:staff_list"))
        self.assertContains(response, "teacher@north.example.test")
        self.assertNotContains(response, "outsider@south.example.test")

    def test_super_admin_without_school_is_redirected(self):
        root = User.objects.create_superuser(
            email="root@platform.example.test", password="a-strong-test-password"
        )
        self.client.force_login(root)
        response = self.client.get(reverse("accounts:staff_create"))
        self.assertRedirects(response, reverse("tenancy:school_list"))


class ParentAccountTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="North School", slug="north", email="north@example.test")
        self.other = School.objects.create(name="South School", slug="south", email="south@example.test")
        self.admin = User.objects.create_user(
            email="admin@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.SCHOOL_ADMIN,
        )
        with school_context(self.school):
            self.student = Student.objects.create(
                admission_number="A-1", first_name="Ada", last_name="Lovelace"
            )

    def _payload(self, student, email="mary@north.example.test"):
        return {
            "first_name": "Mary",
            "last_name": "Lovelace",
            "email": email,
            "student": student.pk,
            "relationship": "Mother",
            "is_primary": "on",
            "password1": "a-strong-test-password",
            "password2": "a-strong-test-password",
        }

    def test_creating_parent_also_links_the_student(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("accounts:parent_create"), self._payload(self.student))
        self.assertRedirects(response, reverse("accounts:parent_list"))
        parent = User.objects.get(email="mary@north.example.test")
        self.assertEqual(parent.role, User.Role.PARENT_STUDENT)
        with school_context(self.school):
            link = Guardian.objects.get(user=parent)
            self.assertEqual(link.student, self.student)
            self.assertTrue(link.is_primary)

    def test_parent_form_only_lists_own_school_students(self):
        with school_context(self.other):
            Student.objects.create(admission_number="B-1", first_name="Alan", last_name="Turing")
        self.client.force_login(self.admin)
        response = self.client.get(reverse("accounts:parent_create"))
        self.assertContains(response, "Lovelace")
        self.assertNotContains(response, "Turing")

    def test_cannot_link_a_student_from_another_school(self):
        with school_context(self.other):
            outsider = Student.objects.create(
                admission_number="B-1", first_name="Alan", last_name="Turing"
            )
        self.client.force_login(self.admin)
        response = self.client.post(reverse("accounts:parent_create"), self._payload(outsider))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="mary@north.example.test").exists())

    def test_parent_list_shows_linked_students(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("accounts:parent_create"), self._payload(self.student))
        response = self.client.get(reverse("accounts:parent_list"))
        self.assertContains(response, "Mary")
        self.assertContains(response, "Ada Lovelace")
