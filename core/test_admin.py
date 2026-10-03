from django.contrib import admin
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from students.models import Student
from tenancy.context import school_context
from tenancy.models import School


def admin_info(model):
    return (model._meta.app_label, model._meta.model_name)


class AdminTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="North School", slug="north", email="north@example.test")
        self.other = School.objects.create(name="South School", slug="south", email="south@example.test")
        self.superuser = User.objects.create_superuser(
            email="root@platform.example.test", password="a-strong-test-password"
        )
        # A staff account that is not a superuser: the admin stays scoped for them.
        self.scoped_staff = User.objects.create_user(
            email="platform@platform.example.test",
            password="a-strong-test-password",
            role=User.Role.SUPER_ADMIN,
            is_staff=True,
        )
        self.client.force_login(self.superuser)

    def _open_school(self):
        self.client.post(reverse("tenancy:school_open", args=[self.school.pk]))

    def _seed_two_schools(self):
        with school_context(self.school):
            Student.objects.create(admission_number="A-1", first_name="Ada", last_name="Lovelace")
        with school_context(self.other):
            Student.objects.create(admission_number="B-1", first_name="Alan", last_name="Turing")

    def test_admin_index_loads(self):
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_every_registered_page_loads(self):
        for model in admin.site._registry:
            if model._meta.app_label == "auth":
                continue
            info = admin_info(model)
            self.assertEqual(
                self.client.get(reverse("admin:%s_%s_changelist" % info)).status_code,
                200,
                info,
            )
            self.assertEqual(
                self.client.get(reverse("admin:%s_%s_add" % info)).status_code, 200, info
            )

    def test_superuser_sees_records_from_every_school(self):
        self._seed_two_schools()
        response = self.client.get(reverse("admin:students_student_changelist"))
        self.assertContains(response, "Lovelace")
        self.assertContains(response, "Turing")

    def test_superuser_can_add_a_student_and_choose_the_school(self):
        self.client.post(
            reverse("admin:students_student_add"),
            {
                "school": self.other.pk,
                "admission_number": "B-2",
                "first_name": "Grace",
                "last_name": "Hopper",
                "is_active": "on",
            },
        )
        with school_context(self.other):
            student = Student.objects.get(admission_number="B-2")
        self.assertEqual(student.school, self.other)

    def test_scoped_staff_stay_limited_to_the_active_school(self):
        # Give the account the permissions a real scoped admin would hold.
        perms = Permission.objects.filter(
            codename__in=["view_student", "add_student", "change_student"]
        )
        self.scoped_staff.user_permissions.set(perms)
        self.scoped_staff = User.objects.get(pk=self.scoped_staff.pk)
        self.client.force_login(self.scoped_staff)

        add_page = reverse("admin:students_student_add")
        self.assertEqual(self.client.get(add_page).status_code, 403)

        listing = self.client.get(reverse("admin:students_student_changelist"), follow=True)
        self.assertContains(listing, "No school is active")

    def test_non_staff_cannot_open_the_admin(self):
        member = User.objects.create_user(
            email="admin@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.SCHOOL_ADMIN,
        )
        self.client.force_login(member)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)
