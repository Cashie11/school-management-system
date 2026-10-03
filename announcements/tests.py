from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from academics.models import AcademicTerm, ClassSubject, SchoolClass, Subject
from accounts.models import User
from students.models import Enrollment, Guardian, Student
from tenancy.context import school_context
from tenancy.models import School

from .models import Announcement
from .selectors import visible_announcements
from .services import purge_expired


class AnnouncementFixtureMixin:
    def setUp(self):
        self.school = School.objects.create(name="North School", slug="north", email="north@example.test")
        self.admin = User.objects.create_user(
            email="admin@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.SCHOOL_ADMIN,
        )
        self.teacher_a = User.objects.create_user(
            email="teacher.a@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.TEACHER,
        )
        self.teacher_b = User.objects.create_user(
            email="teacher.b@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.TEACHER,
        )
        self.parent_a = User.objects.create_user(
            email="parent.a@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.PARENT_STUDENT,
        )
        self.parent_b = User.objects.create_user(
            email="parent.b@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.PARENT_STUDENT,
        )

        with school_context(self.school):
            self.term = AcademicTerm.objects.create(
                name="Term 1", start_date="2026-01-10", end_date="2026-04-10", is_current=True
            )
            self.class_a = SchoolClass.objects.create(name="Grade 6", level=6)
            self.class_b = SchoolClass.objects.create(name="Grade 7", level=7)
            subject = Subject.objects.create(name="Mathematics")
            ClassSubject.objects.create(
                school_class=self.class_a, subject=subject, teacher=self.teacher_a
            )
            ClassSubject.objects.create(
                school_class=self.class_b, subject=subject, teacher=self.teacher_b
            )
            student_a = Student.objects.create(
                admission_number="A-1", first_name="Ada", last_name="Lovelace"
            )
            student_b = Student.objects.create(
                admission_number="B-1", first_name="Alan", last_name="Turing"
            )
            Enrollment.objects.create(student=student_a, school_class=self.class_a, term=self.term)
            Enrollment.objects.create(student=student_b, school_class=self.class_b, term=self.term)
            Guardian.objects.create(user=self.parent_a, student=student_a)
            Guardian.objects.create(user=self.parent_b, student=student_b)

    def _announce(self, title, **kwargs):
        with school_context(self.school):
            return Announcement.objects.create(title=title, body="Body", **kwargs)

    def _titles_for(self, user):
        with school_context(self.school):
            return list(visible_announcements(user).values_list("title", flat=True))


class AnnouncementTests(AnnouncementFixtureMixin, TestCase):
    def test_everyone_announcement_reaches_every_role(self):
        self._announce("School closed", audience=Announcement.Audience.EVERYONE)
        for user in (self.admin, self.teacher_a, self.parent_a):
            self.assertIn("School closed", self._titles_for(user), user.email)

    def test_teacher_announcement_is_hidden_from_families(self):
        self._announce("Staff briefing", audience=Announcement.Audience.TEACHERS)
        self.assertIn("Staff briefing", self._titles_for(self.teacher_a))
        self.assertNotIn("Staff briefing", self._titles_for(self.parent_a))

    def test_family_announcement_is_hidden_from_teachers(self):
        self._announce("Fees due", audience=Announcement.Audience.STUDENTS)
        self.assertIn("Fees due", self._titles_for(self.parent_a))
        self.assertNotIn("Fees due", self._titles_for(self.teacher_a))

    def test_class_announcement_only_reaches_that_class(self):
        self._announce(
            "Grade 6 trip", audience=Announcement.Audience.STUDENTS, school_class=self.class_a
        )
        self.assertIn("Grade 6 trip", self._titles_for(self.parent_a))
        self.assertNotIn("Grade 6 trip", self._titles_for(self.parent_b))
        # The teacher of that class sees it too.
        self.assertIn("Grade 6 trip", self._titles_for(self.teacher_a))

    def test_expired_announcements_are_hidden(self):
        self._announce(
            "Old news",
            audience=Announcement.Audience.EVERYONE,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        self.assertNotIn("Old news", self._titles_for(self.admin))

    def test_pinned_announcements_sort_first(self):
        self._announce("Ordinary", audience=Announcement.Audience.EVERYONE)
        self._announce("Pinned", audience=Announcement.Audience.EVERYONE, is_pinned=True)
        self.assertEqual(self._titles_for(self.admin)[0], "Pinned")

    def test_a_parent_cannot_create_an_announcement(self):
        self.client.force_login(self.parent_a)
        response = self.client.get(reverse("announcements:create"))
        self.assertEqual(response.status_code, 403)

    def test_a_teacher_posts_to_their_own_class(self):
        self.client.force_login(self.teacher_a)
        response = self.client.post(
            reverse("announcements:create"),
            {
                "audience": Announcement.Audience.STUDENTS,
                "school_class": self.class_a.pk,
                "title": "Test moved to Friday",
                "body": "The test moves to Friday.",
            },
        )
        self.assertRedirects(response, reverse("announcements:list"))
        with school_context(self.school):
            announcement = Announcement.objects.get()
            self.assertEqual(announcement.author, self.teacher_a)
            self.assertEqual(announcement.school_class, self.class_a)

    def test_a_teacher_cannot_post_to_another_class(self):
        self.client.force_login(self.teacher_a)
        response = self.client.post(
            reverse("announcements:create"),
            {
                "audience": Announcement.Audience.STUDENTS,
                "school_class": self.class_b.pk,
                "title": "Not mine",
                "body": "Should not be created.",
            },
        )
        self.assertEqual(response.status_code, 200)
        with school_context(self.school):
            self.assertEqual(Announcement.objects.count(), 0)

    def test_a_teacher_cannot_broadcast_to_the_whole_school(self):
        self.client.force_login(self.teacher_a)
        response = self.client.post(
            reverse("announcements:create"),
            {
                "audience": Announcement.Audience.EVERYONE,
                "school_class": self.class_a.pk,
                "title": "Broadcast",
                "body": "Should not be created.",
            },
        )
        self.assertEqual(response.status_code, 200)
        with school_context(self.school):
            self.assertEqual(Announcement.objects.count(), 0)

    def test_a_teacher_cannot_edit_another_teachers_announcement(self):
        announcement = self._announce(
            "Grade 6 trip", audience=Announcement.Audience.STUDENTS, school_class=self.class_a
        )
        with school_context(self.school):
            announcement.author = self.teacher_a
            announcement.save(update_fields=["author"])

        self.client.force_login(self.teacher_b)
        response = self.client.get(reverse("announcements:edit", args=[announcement.pk]))
        self.assertEqual(response.status_code, 403)

    def test_an_admin_can_edit_any_announcement(self):
        announcement = self._announce("Notice", audience=Announcement.Audience.EVERYONE)
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("announcements:edit", args=[announcement.pk]),
            {
                "audience": Announcement.Audience.EVERYONE,
                "title": "Notice updated",
                "body": "New body",
            },
        )
        self.assertRedirects(response, reverse("announcements:list"))
        with school_context(self.school):
            announcement.refresh_from_db()
        self.assertEqual(announcement.title, "Notice updated")

    def test_the_dashboard_shows_announcements(self):
        self._announce("Sports day", audience=Announcement.Audience.EVERYONE)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard:home"))
        self.assertContains(response, "Sports day")

    def test_the_announcement_page_offers_a_create_button(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("announcements:list"))
        self.assertContains(response, reverse("announcements:create"))

        self.client.force_login(self.teacher_a)
        response = self.client.get(reverse("announcements:list"))
        self.assertContains(response, reverse("announcements:create"))

    def test_a_parent_is_not_offered_a_create_button(self):
        self.client.force_login(self.parent_a)
        response = self.client.get(reverse("announcements:list"))
        self.assertNotContains(response, reverse("announcements:create"))

    def test_the_dashboard_links_to_creating_an_announcement(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard:home"))
        self.assertContains(response, reverse("announcements:create"))

        self.client.force_login(self.teacher_a)
        response = self.client.get(reverse("dashboard:home"))
        self.assertContains(response, reverse("announcements:create"))

        self.client.force_login(self.parent_a)
        response = self.client.get(reverse("portal:home"))
        self.assertNotContains(response, reverse("announcements:create"))

    def test_a_parent_sees_announcements_on_the_portal(self):
        self._announce(
            "Grade 6 trip", audience=Announcement.Audience.STUDENTS, school_class=self.class_a
        )
        self.client.force_login(self.parent_a)
        response = self.client.get(reverse("portal:home"))
        self.assertContains(response, "Grade 6 trip")


class AnnouncementLifecycleTests(AnnouncementFixtureMixin, TestCase):
    def test_an_admin_can_delete_an_announcement(self):
        announcement = self._announce("Temporary", audience=Announcement.Audience.EVERYONE)
        self.client.force_login(self.admin)
        response = self.client.post(reverse("announcements:delete", args=[announcement.pk]))
        self.assertRedirects(response, reverse("announcements:list"))
        with school_context(self.school):
            self.assertEqual(Announcement.objects.count(), 0)

    def test_a_teacher_can_edit_their_own_class_announcement(self):
        announcement = self._announce(
            "Notice", audience=Announcement.Audience.STUDENTS, school_class=self.class_a
        )
        with school_context(self.school):
            announcement.author = self.teacher_a
            announcement.save(update_fields=["author"])

        self.client.force_login(self.teacher_a)
        response = self.client.post(
            reverse("announcements:edit", args=[announcement.pk]),
            {
                "audience": Announcement.Audience.STUDENTS,
                "school_class": self.class_a.pk,
                "title": "Notice updated",
                "body": "Updated body",
            },
        )
        self.assertRedirects(response, reverse("announcements:list"))
        with school_context(self.school):
            announcement.refresh_from_db()
        self.assertEqual(announcement.title, "Notice updated")
        self.assertEqual(announcement.body, "Updated body")

    def test_purge_removes_only_expired_announcements(self):
        self._announce(
            "Old", audience=Announcement.Audience.EVERYONE, expires_at=timezone.now() - timedelta(hours=1)
        )
        self._announce(
            "Current", audience=Announcement.Audience.EVERYONE, expires_at=timezone.now() + timedelta(hours=1)
        )
        self._announce("No expiry", audience=Announcement.Audience.EVERYONE)

        with school_context(self.school):
            self.assertEqual(purge_expired(), 1)
            titles = set(Announcement.objects.values_list("title", flat=True))
        self.assertEqual(titles, {"Current", "No expiry"})

    def test_the_purge_command_runs(self):
        self._announce(
            "Old", audience=Announcement.Audience.EVERYONE, expires_at=timezone.now() - timedelta(hours=1)
        )
        call_command("purge_expired_announcements")
        with school_context(self.school):
            self.assertEqual(Announcement.objects.count(), 0)

    def test_the_cleanup_task_is_scheduled(self):
        from config.celery import app

        app.loader.import_default_modules()
        self.assertIn("announcements.tasks.purge_expired_announcements", app.tasks)
