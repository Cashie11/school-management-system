from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from tenancy.models import School


class PublicPageTests(TestCase):
    def test_home_page_renders(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Multi-tenant school platform")

    def test_login_page_renders(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in")


class SchoolSignupTests(TestCase):
    def _signup(self, **overrides):
        data = {
            "school_name": "Harbor School",
            "school_email": "office@harbor.example.test",
            "admin_email": "admin@harbor.example.test",
            "password1": "a-strong-test-password",
            "password2": "a-strong-test-password",
        }
        data.update(overrides)
        return self.client.post(reverse("accounts:signup"), data)

    def test_signup_creates_school_admin_and_signs_in(self):
        response = self._signup()
        self.assertRedirects(response, reverse("dashboard:home"))

        school = School.objects.get(slug="harbor-school")
        admin = User.objects.get(email="admin@harbor.example.test")
        self.assertEqual(admin.school, school)
        self.assertEqual(admin.role, User.Role.SCHOOL_ADMIN)
        self.assertIn("_auth_user_id", self.client.session)

        dashboard = self.client.get(reverse("dashboard:home"))
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, "Harbor School")

    def test_signup_rejects_mismatched_passwords(self):
        response = self._signup(password2="a-different-password")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(School.objects.count(), 0)

    def test_signup_rejects_duplicate_admin_email(self):
        self._signup()
        self.client.logout()
        response = self._signup(
            school_name="Second School", admin_email="ADMIN@harbor.example.test"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(School.objects.count(), 1)


class LoginTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="North School", slug="north", email="north@example.test")
        self.user = User.objects.create_user(
            email="admin@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.SCHOOL_ADMIN,
        )

    def test_login_is_case_insensitive(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "Admin@North.Example.Test", "password": "a-strong-test-password"},
        )
        self.assertRedirects(response, reverse("dashboard:home"))

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        get_response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(get_response.status_code, 405)
        post_response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(post_response, reverse("core:home"))


class SuperAdminTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="North School", slug="north", email="north@example.test")
        self.super_admin = User.objects.create_superuser(
            email="root@platform.example.test", password="a-strong-test-password"
        )
        self.teacher = User.objects.create_user(
            email="teacher@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.TEACHER,
        )

    def test_super_admin_sees_the_platform_dashboard(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Platform")
        self.assertContains(response, "North School")

    def test_school_list_is_restricted_to_super_admins(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("tenancy:school_list"))
        self.assertEqual(response.status_code, 403)

    def test_opening_a_school_establishes_tenant_context(self):
        self.client.force_login(self.super_admin)
        response = self.client.post(reverse("tenancy:school_open", args=[self.school.pk]))
        self.assertRedirects(response, reverse("dashboard:home"))
        self.assertEqual(self.client.session["active_school_id"], self.school.pk)

        dashboard = self.client.get(reverse("dashboard:home"))
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, "North School")
