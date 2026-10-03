from django.test import Client, TestCase
from django.urls import reverse

from students.models import Guardian, Student
from tenancy.context import school_context
from tenancy.models import School

from .models import User


class AccountManagementTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="North School", slug="north", email="north@example.test")
        self.other = School.objects.create(name="South School", slug="south", email="south@example.test")
        self.admin = User.objects.create_user(
            email="admin@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.SCHOOL_ADMIN,
        )
        self.teacher = User.objects.create_user(
            email="teacher@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.TEACHER,
        )
        self.outsider = User.objects.create_user(
            email="teacher@south.example.test",
            password="a-strong-test-password",
            school=self.other,
            role=User.Role.TEACHER,
        )
        self.client.force_login(self.admin)

    def test_admin_suspends_and_reactivates_a_teacher(self):
        self.client.post(reverse("accounts:user_toggle_active", args=[self.teacher.pk]))
        self.teacher.refresh_from_db()
        self.assertFalse(self.teacher.is_active)

        self.client.post(reverse("accounts:user_toggle_active", args=[self.teacher.pk]))
        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.is_active)

    def test_a_suspended_account_cannot_sign_in(self):
        self.client.post(reverse("accounts:user_toggle_active", args=[self.teacher.pk]))
        self.client.logout()
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "teacher@north.example.test", "password": "a-strong-test-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_suspending_revokes_an_existing_session(self):
        # The teacher is already signed in.
        teacher_client = Client()
        teacher_client.force_login(self.teacher)
        self.assertEqual(teacher_client.get(reverse("dashboard:home")).status_code, 200)

        # The school admin suspends them.
        self.client.force_login(self.admin)
        self.client.post(reverse("accounts:user_toggle_active", args=[self.teacher.pk]))

        # The teacher's next request must not reach a protected page.
        dashboard = teacher_client.get(reverse("dashboard:home"))
        self.assertEqual(dashboard.status_code, 302)
        self.assertIn("/accounts/login/", dashboard.url)

        attendance = teacher_client.get(reverse("attendance:register"))
        self.assertEqual(attendance.status_code, 302)
        self.assertIn("/accounts/login/", attendance.url)

    def test_a_suspended_account_is_told_why_at_login(self):
        self.client.post(reverse("accounts:user_toggle_active", args=[self.teacher.pk]))
        self.client.logout()
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "teacher@north.example.test", "password": "a-strong-test-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "suspended")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_a_removed_account_is_told_why_at_login(self):
        self.client.post(reverse("accounts:user_delete", args=[self.teacher.pk]))
        self.client.logout()
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "teacher@north.example.test", "password": "a-strong-test-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "was removed")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_a_wrong_password_still_says_nothing_extra(self):
        self.client.logout()
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "teacher@north.example.test", "password": "definitely-wrong"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "suspended")
        self.assertNotContains(response, "was removed")

    def test_admin_cannot_suspend_their_own_account(self):
        self.client.post(reverse("accounts:user_toggle_active", args=[self.admin.pk]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_the_only_school_admin_cannot_be_removed(self):
        # A platform Super Admin working inside the school would otherwise lock it out.
        root = User.objects.create_superuser(
            email="root@platform.example.test", password="a-strong-test-password"
        )
        self.client.force_login(root)
        self.client.post(reverse("tenancy:school_open", args=[self.school.pk]))

        self.client.post(reverse("accounts:user_toggle_active", args=[self.admin.pk]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_removing_a_teacher_hides_and_blocks_the_account(self):
        response = self.client.post(reverse("accounts:user_delete", args=[self.teacher.pk]))
        self.assertEqual(response.status_code, 302)

        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.is_removed)
        self.assertFalse(self.teacher.is_active)

        # The first load consumes the flash message, which quotes the email.
        self.client.get(reverse("accounts:staff_list"))
        listing = self.client.get(reverse("accounts:staff_list"))
        self.assertNotContains(listing, "teacher@north.example.test")

    def test_re_adding_a_removed_account_restores_it(self):
        self.client.post(reverse("accounts:user_delete", args=[self.teacher.pk]))

        response = self.client.post(
            reverse("accounts:staff_create"),
            {
                "first_name": "Eke",
                "last_name": "Orie",
                "email": "teacher@north.example.test",
                "role": User.Role.TEACHER,
                "password1": "a-strong-test-password",
                "password2": "a-strong-test-password",
            },
        )
        self.assertRedirects(response, reverse("accounts:staff_list"))

        self.teacher.refresh_from_db()
        self.assertFalse(self.teacher.is_removed)
        self.assertTrue(self.teacher.is_active)
        self.assertEqual(User.objects.filter(email="teacher@north.example.test").count(), 1)

    def test_removing_a_parent_keeps_the_student_record(self):
        parent = User.objects.create_user(
            email="parent@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.PARENT_STUDENT,
        )
        with school_context(self.school):
            student = Student.objects.create(
                admission_number="A-1", first_name="Ada", last_name="Lovelace"
            )
            Guardian.objects.create(user=parent, student=student)

        self.client.post(reverse("accounts:user_delete", args=[parent.pk]))

        with school_context(self.school):
            self.assertTrue(Student.objects.filter(pk=student.pk).exists())
            self.assertEqual(Guardian.objects.count(), 0)

    def test_another_schools_account_is_not_reachable(self):
        response = self.client.post(
            reverse("accounts:user_toggle_active", args=[self.outsider.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.outsider.refresh_from_db()
        self.assertTrue(self.outsider.is_active)

    def test_toggle_requires_post(self):
        response = self.client.get(reverse("accounts:user_toggle_active", args=[self.teacher.pk]))
        self.assertEqual(response.status_code, 405)

    def test_teachers_cannot_manage_accounts(self):
        self.client.force_login(self.teacher)
        response = self.client.post(
            reverse("accounts:user_toggle_active", args=[self.admin.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_staff_list_offers_the_controls(self):
        response = self.client.get(reverse("accounts:staff_list"))
        self.assertContains(response, "Suspend")
        self.assertContains(response, "Remove")
