from django.core import mail
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from tenancy.models import School

from .models import SupportMessage


class HelpCentreTests(TestCase):
    def test_the_help_index_lists_guides(self):
        response = self.client.get(reverse("support:help"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Getting started")
        self.assertContains(response, "Recording attendance")

    def test_a_guide_renders(self):
        response = self.client.get(reverse("support:article", args=["getting-started"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Register the school")

    def test_an_unknown_guide_is_a_404(self):
        response = self.client.get(reverse("support:article", args=["does-not-exist"]))
        self.assertEqual(response.status_code, 404)


class ContactFormTests(TestCase):
    def payload(self, **overrides):
        data = {
            "name": "A Parent",
            "email": "parent@example.test",
            "subject": "Cannot see results",
            "body": "The results page is empty for my child this term.",
            "website": "",
        }
        data.update(overrides)
        return data

    def test_the_contact_page_renders(self):
        response = self.client.get(reverse("support:contact"))
        self.assertEqual(response.status_code, 200)

    def test_a_message_is_stored_and_emailed(self):
        response = self.client.post(reverse("support:contact"), self.payload())
        self.assertRedirects(response, reverse("support:contact_done"))

        message = SupportMessage.objects.get()
        self.assertEqual(message.subject, "Cannot see results")
        self.assertEqual(message.status, SupportMessage.Status.NEW)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Cannot see results", mail.outbox[0].subject)
        self.assertIn("parent@example.test", mail.outbox[0].reply_to)

    def test_a_honeypot_submission_is_dropped(self):
        response = self.client.post(
            reverse("support:contact"), self.payload(website="http://spam.example.test")
        )
        # The bot still sees the normal confirmation, but nothing is stored or sent.
        self.assertRedirects(response, reverse("support:contact_done"))
        self.assertEqual(SupportMessage.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_a_too_short_message_is_rejected(self):
        response = self.client.post(reverse("support:contact"), self.payload(body="help"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(SupportMessage.objects.count(), 0)

    def test_a_signed_in_sender_records_their_school(self):
        school = School.objects.create(
            name="North School", slug="north", email="north@example.test"
        )
        user = User.objects.create_user(
            email="parent@north.example.test",
            password="a-strong-test-password",
            school=school,
            role=User.Role.PARENT_STUDENT,
        )
        self.client.force_login(user)

        self.client.post(reverse("support:contact"), self.payload())
        self.assertEqual(SupportMessage.objects.get().school, school)


class SupportInboxTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="North School", slug="north", email="north@example.test"
        )
        SupportMessage.objects.create(
            name="A Parent",
            email="parent@example.test",
            subject="Cannot see results",
            body="The results page is empty.",
        )

    def test_a_super_admin_sees_the_inbox(self):
        super_admin = User.objects.create_user(
            email="root@example.test",
            password="a-strong-test-password",
            role=User.Role.SUPER_ADMIN,
        )
        self.client.force_login(super_admin)

        response = self.client.get(reverse("support:message_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cannot see results")

    def test_a_school_admin_cannot_see_the_inbox(self):
        admin = User.objects.create_user(
            email="admin@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.SCHOOL_ADMIN,
        )
        self.client.force_login(admin)

        response = self.client.get(reverse("support:message_list"))
        self.assertEqual(response.status_code, 403)

    def test_resolving_marks_the_message(self):
        super_admin = User.objects.create_user(
            email="root@example.test",
            password="a-strong-test-password",
            role=User.Role.SUPER_ADMIN,
        )
        self.client.force_login(super_admin)

        message = SupportMessage.objects.get()
        response = self.client.post(reverse("support:message_resolve", args=[message.pk]))
        self.assertRedirects(response, reverse("support:message_list"))

        message.refresh_from_db()
        self.assertEqual(message.status, SupportMessage.Status.RESOLVED)
