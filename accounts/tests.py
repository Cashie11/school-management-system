from django.contrib.auth import authenticate
from django.test import TestCase

from .models import User
from .services import register_school


class SchoolOnboardingTests(TestCase):
    def test_signup_creates_school_and_school_admin(self):
        school, admin = register_school(
            school_name="Harbor School",
            school_email="office@harbor.example.test",
            admin_email="admin@harbor.example.test",
            password="a-strong-test-password",
        )

        self.assertEqual(school.slug, "harbor-school")
        self.assertEqual(admin.school, school)
        self.assertEqual(admin.role, User.Role.SCHOOL_ADMIN)
        self.assertEqual(
            authenticate(email="admin@harbor.example.test", password="a-strong-test-password"),
            admin,
        )

    def test_school_signup_uses_a_unique_slug(self):
        register_school(
            school_name="Harbor School",
            school_email="office@harbor.example.test",
            admin_email="first@harbor.example.test",
            password="a-strong-test-password",
        )
        second_school, _ = register_school(
            school_name="Harbor School",
            school_email="office2@harbor.example.test",
            admin_email="second@harbor.example.test",
            password="a-strong-test-password",
        )

        self.assertEqual(second_school.slug, "harbor-school-2")