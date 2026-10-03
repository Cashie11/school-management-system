import re

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from tenancy.models import School

from .models import User

NEW_PASSWORD = "a-brand-new-strong-password"


class PasswordResetTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="North School", slug="north", email="north@example.test")
        self.user = User.objects.create_user(
            email="admin@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.SCHOOL_ADMIN,
        )

    def _reset_link(self):
        body = mail.outbox[0].body
        match = re.search(r"http://[^\s]+/accounts/password-reset/[^\s]+", body)
        return match.group(0)

    def test_reset_form_renders(self):
        response = self.client.get(reverse("accounts:password_reset"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reset your password")

    def test_known_email_receives_a_reset_link(self):
        response = self.client.post(
            reverse("accounts:password_reset"), {"email": "admin@north.example.test"}
        )
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("password", mail.outbox[0].subject.lower())
        self.assertIn("/accounts/password-reset/", mail.outbox[0].body)

    def test_unknown_email_looks_identical(self):
        response = self.client.post(
            reverse("accounts:password_reset"), {"email": "nobody@example.test"}
        )
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)

    def test_suspended_and_removed_accounts_get_no_reset_mail(self):
        self.client.post(reverse("accounts:password_reset"), {"email": "admin@north.example.test"})
        self.assertEqual(len(mail.outbox), 1)
        mail.outbox.clear()

        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.client.post(reverse("accounts:password_reset"), {"email": "admin@north.example.test"})
        self.assertEqual(len(mail.outbox), 0)

    def test_full_reset_lets_the_user_sign_in_with_the_new_password(self):
        self.client.post(reverse("accounts:password_reset"), {"email": "admin@north.example.test"})
        link = self._reset_link()

        response = self.client.get(link, follow=True)
        self.assertEqual(response.status_code, 200)
        confirm_url = response.redirect_chain[-1][0] if response.redirect_chain else link

        response = self.client.post(
            confirm_url, {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD}
        )
        self.assertRedirects(response, reverse("accounts:password_reset_complete"))

        self.client.logout()
        signed_in = self.client.post(
            reverse("accounts:login"),
            {"username": "admin@north.example.test", "password": NEW_PASSWORD},
        )
        self.assertRedirects(signed_in, reverse("dashboard:home"))

    def test_an_invalid_link_is_reported(self):
        response = self.client.get(
            reverse(
                "accounts:password_reset_confirm",
                kwargs={"uidb64": "invalid", "token": "invalid-token"},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "expired")


class PasswordChangeTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="North School", slug="north", email="north@example.test")
        self.user = User.objects.create_user(
            email="admin@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.SCHOOL_ADMIN,
        )

    def test_change_requires_a_signed_in_user(self):
        response = self.client.get(reverse("accounts:password_change"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_a_signed_in_user_can_change_their_password(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": "a-strong-test-password",
                "new_password1": NEW_PASSWORD,
                "new_password2": NEW_PASSWORD,
            },
        )
        self.assertRedirects(response, reverse("accounts:password_change_done"))

        self.client.logout()
        signed_in = self.client.post(
            reverse("accounts:login"),
            {"username": "admin@north.example.test", "password": NEW_PASSWORD},
        )
        self.assertRedirects(signed_in, reverse("dashboard:home"))

    def test_a_wrong_current_password_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": "not-the-password",
                "new_password1": NEW_PASSWORD,
                "new_password2": NEW_PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("a-strong-test-password"))
