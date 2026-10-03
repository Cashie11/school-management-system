from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from tenancy.models import School


class BackControlTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="North School", slug="north", email="north@example.test")
        self.admin = User.objects.create_user(
            email="admin@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.SCHOOL_ADMIN,
        )
        self.client.force_login(self.admin)

    def test_the_dashboard_has_no_back_control(self):
        response = self.client.get(reverse("dashboard:home"))
        self.assertNotContains(response, 'class="back-row"')

    def test_the_landing_page_has_no_back_control(self):
        self.client.logout()
        response = self.client.get(reverse("core:home"))
        self.assertNotContains(response, 'class="back-row"')

    def test_the_sign_in_page_has_no_back_control(self):
        self.client.logout()
        response = self.client.get(reverse("accounts:login"))
        self.assertNotContains(response, 'class="back-row"')

    def test_inner_pages_have_a_back_control(self):
        for name in (
            "students:student_list",
            "academics:term_list",
            "attendance:register",
            "results:assessment_list",
            "accounts:staff_list",
            "dashboard:class_list",
        ):
            response = self.client.get(reverse(name))
            self.assertContains(response, 'class="back-row"', msg_prefix=name)

    def test_the_back_control_falls_back_to_the_dashboard(self):
        response = self.client.get(reverse("students:student_list"))
        self.assertContains(response, 'data-back-fallback="/dashboard/"')
