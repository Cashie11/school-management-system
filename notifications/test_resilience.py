from unittest import mock

from django.core import mail
from django.test import TestCase

from students.models import Student
from tenancy.context import school_context
from tenancy.models import School

from .models import EmailLog
from .services import notify_student_welcome


class NotificationResilienceTests(TestCase):
    """A notification failure must never break the request that caused it."""

    def setUp(self):
        self.school = School.objects.create(name="North School", slug="north", email="north@example.test")
        with school_context(self.school):
            self.student = Student.objects.create(
                admission_number="A-1",
                first_name="Ada",
                last_name="Lovelace",
                email="ada@example.test",
            )

    def test_a_render_failure_is_swallowed(self):
        with mock.patch(
            "notifications.services.render_to_string",
            side_effect=RuntimeError("missing template"),
        ):
            with school_context(self.school):
                self.assertEqual(notify_student_welcome(self.student), 1)
                self.assertEqual(len(mail.outbox), 0)

    def test_a_logging_failure_is_swallowed(self):
        with mock.patch(
            "notifications.services.EmailLog.objects.create",
            side_effect=RuntimeError("database is unhappy"),
        ):
            with school_context(self.school):
                # The mail still goes out; only the record is lost.
                self.assertEqual(notify_student_welcome(self.student), 1)
        with school_context(self.school):
            self.assertEqual(EmailLog.objects.count(), 0)

    def test_a_send_failure_is_swallowed(self):
        with mock.patch(
            "notifications.services.EmailMultiAlternatives.send",
            side_effect=RuntimeError("smtp is down"),
        ):
            with school_context(self.school):
                self.assertEqual(notify_student_welcome(self.student), 1)
                self.assertEqual(len(mail.outbox), 0)
