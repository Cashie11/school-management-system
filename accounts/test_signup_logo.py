import tempfile
from io import BytesIO
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from tenancy.models import School

from .models import User


def make_image(name="logo.png", size=(200, 200), fmt="PNG"):
    buffer = BytesIO()
    Image.new("RGB", size, "#e6fb2d").save(buffer, format=fmt)
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type="image/png")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class SchoolLogoSignupTests(TestCase):
    def _payload(self, **overrides):
        data = {
            "school_name": "Harbor School",
            "school_email": "office@harbor.example.test",
            "admin_email": "admin@harbor.example.test",
            "password1": "a-strong-test-password",
            "password2": "a-strong-test-password",
        }
        data.update(overrides)
        return data

    def test_signup_can_attach_a_logo(self):
        response = self.client.post(
            reverse("accounts:signup"), self._payload(logo=make_image())
        )
        self.assertRedirects(response, reverse("dashboard:home"))

        school = School.objects.get()
        self.assertTrue(school.logo)
        self.assertTrue(school.logo.name.startswith("school-logos/"))

    def test_signup_works_without_a_logo(self):
        response = self.client.post(reverse("accounts:signup"), self._payload())
        self.assertRedirects(response, reverse("dashboard:home"))
        self.assertFalse(School.objects.get().logo)

    def test_a_tiny_logo_is_rejected(self):
        response = self.client.post(
            reverse("accounts:signup"), self._payload(logo=make_image(size=(32, 32)))
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(School.objects.count(), 0)

    def test_a_non_image_is_rejected(self):
        bad = SimpleUploadedFile("logo.png", b"this is not an image", content_type="image/png")
        response = self.client.post(reverse("accounts:signup"), self._payload(logo=bad))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(School.objects.count(), 0)

    def test_an_oversized_logo_is_rejected(self):
        big = SimpleUploadedFile(
            "logo.png", b"x" * (2 * 1024 * 1024 + 1), content_type="image/png"
        )
        response = self.client.post(reverse("accounts:signup"), self._payload(logo=big))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(School.objects.count(), 0)

    def test_an_image_bomb_is_rejected(self):
        with mock.patch.object(Image, "MAX_IMAGE_PIXELS", 100):
            response = self.client.post(
                reverse("accounts:signup"), self._payload(logo=make_image(size=(200, 200)))
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(School.objects.count(), 0)

    def test_the_brand_shows_the_school_name(self):
        self.client.post(reverse("accounts:signup"), self._payload(logo=make_image()))
        dashboard = self.client.get(reverse("dashboard:home"))
        self.assertContains(dashboard, "Harbor School")
        self.assertContains(dashboard, "brand-logo")

    def test_the_brand_falls_back_to_an_icon_without_a_logo(self):
        self.client.post(reverse("accounts:signup"), self._payload())
        dashboard = self.client.get(reverse("dashboard:home"))
        self.assertContains(dashboard, "bi-mortarboard-fill")
        self.assertContains(dashboard, "Harbor School")

    def test_a_school_admin_can_update_the_profile_later(self):
        self.client.post(reverse("accounts:signup"), self._payload())

        response = self.client.post(
            reverse("accounts:school_profile"),
            {
                "name": "Harbor Academy",
                "email": "hello@harbor.example.test",
                "logo": make_image(),
            },
        )
        self.assertRedirects(response, reverse("accounts:school_profile"))

        school = School.objects.get()
        self.assertEqual(school.name, "Harbor Academy")
        self.assertTrue(school.logo)

    def test_a_teacher_cannot_open_the_school_profile(self):
        self.client.post(reverse("accounts:signup"), self._payload())
        teacher = User.objects.create_user(
            email="teacher@harbor.example.test",
            password="a-strong-test-password",
            school=School.objects.get(),
            role=User.Role.TEACHER,
        )
        self.client.force_login(teacher)
        self.assertEqual(self.client.get(reverse("accounts:school_profile")).status_code, 403)
