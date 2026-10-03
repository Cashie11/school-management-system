"""Tests for the two-pane navigation and the public pages it links to."""

from types import SimpleNamespace

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from core.navigation import build_navigation
from tenancy.models import School


def item_labels(sections):
    return [item["label"] for section in sections for item in section["items"]]


class SideNavigationTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="North School", slug="north", email="north@example.test"
        )

    def make_user(self, role, with_school=True):
        return User.objects.create_user(
            email=f"{role.lower()}@example.test",
            password="a-strong-test-password",
            school=self.school if with_school else None,
            role=role,
        )

    def nav_for(self, user, school_id="auto"):
        if school_id == "auto":
            school_id = user.school_id
        request = SimpleNamespace(user=user, school_id=school_id, resolver_match=None)
        return build_navigation(request)["nav_sections"]

    def test_a_school_admin_can_reach_students_and_add_one(self):
        sections = self.nav_for(self.make_user(User.Role.SCHOOL_ADMIN))
        self.assertIn("students", [section["key"] for section in sections])
        self.assertIn("Add student", item_labels(sections))

    def test_a_teacher_sees_students_but_cannot_add_one(self):
        sections = self.nav_for(self.make_user(User.Role.TEACHER))
        self.assertIn("students", [section["key"] for section in sections])
        self.assertNotIn("Add student", item_labels(sections))

    def test_a_parent_sees_dashboard_announcements_portal_and_support(self):
        sections = self.nav_for(self.make_user(User.Role.PARENT_STUDENT))
        self.assertEqual(
            [section["key"] for section in sections],
            ["dashboard", "announcements", "portal", "support"],
        )

    def test_a_super_admin_without_a_school_sees_platform_sections_only(self):
        user = self.make_user(User.Role.SUPER_ADMIN, with_school=False)
        sections = self.nav_for(user, school_id=None)
        keys = [section["key"] for section in sections]
        self.assertIn("schools", keys)
        self.assertIn("support", keys)
        self.assertNotIn("students", keys)
        self.assertNotIn("dashboard", keys)

    def test_the_support_inbox_is_only_for_super_admins(self):
        admin_sections = self.nav_for(self.make_user(User.Role.SCHOOL_ADMIN))
        self.assertNotIn("Support inbox", item_labels(admin_sections))

        root = self.make_user(User.Role.SUPER_ADMIN, with_school=False)
        root_sections = self.nav_for(root, school_id=None)
        self.assertIn("Support inbox", item_labels(root_sections))

    def test_the_sidebar_is_rendered_for_a_signed_in_admin(self):
        self.client.force_login(self.make_user(User.Role.SCHOOL_ADMIN))
        response = self.client.get(reverse("students:student_list"))
        self.assertContains(response, "data-side-nav")
        self.assertContains(response, "Add student")

    def test_the_matching_section_is_marked_active(self):
        self.client.force_login(self.make_user(User.Role.SCHOOL_ADMIN))
        response = self.client.get(reverse("students:student_list"))
        active = [section["key"] for section in response.context["nav_sections"] if section["active"]]
        self.assertEqual(active, ["students"])

    def test_the_dashboard_page_marks_only_the_dashboard_section_active(self):
        # Dashboard and Classes share the ``dashboard`` namespace, so this guards
        # against both sections lighting up at once.
        self.client.force_login(self.make_user(User.Role.SCHOOL_ADMIN))
        response = self.client.get(reverse("dashboard:home"))
        active = [section["key"] for section in response.context["nav_sections"] if section["active"]]
        self.assertEqual(active, ["dashboard"])

    def test_the_sidebar_has_a_toggle_for_the_section_pane(self):
        self.client.force_login(self.make_user(User.Role.SCHOOL_ADMIN))
        response = self.client.get(reverse("dashboard:home"))
        self.assertContains(response, "data-panel-toggle")
        self.assertContains(response, 'id="side-nav-panel"')

    def test_the_section_pane_has_accordion_toggles(self):
        self.client.force_login(self.make_user(User.Role.SCHOOL_ADMIN))
        response = self.client.get(reverse("students:student_list"))
        self.assertContains(response, "data-section-toggle")
        # The section matching the page starts open; the rest start closed.
        self.assertContains(response, "panel-section is-active is-open")

    def test_the_add_student_page_activates_its_own_item(self):
        self.client.force_login(self.make_user(User.Role.SCHOOL_ADMIN))
        response = self.client.get(reverse("students:student_create"))
        active = [
            item["label"]
            for section in response.context["nav_sections"]
            for item in section["items"]
            if item["active"]
        ]
        self.assertEqual(active, ["Add student"])


class PrivacyPolicyTests(TestCase):
    def test_the_privacy_page_renders(self):
        response = self.client.get(reverse("core:privacy"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Privacy policy")

    def test_the_footer_links_to_the_privacy_policy(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertContains(response, reverse("core:privacy"))

    def test_the_signup_form_links_to_the_privacy_policy(self):
        response = self.client.get(reverse("accounts:signup"))
        self.assertContains(response, reverse("core:privacy"))
