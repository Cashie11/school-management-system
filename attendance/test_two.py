from django.test import TestCase
from django.urls import reverse

from academics.models import AcademicTerm, SchoolClass
from accounts.models import User
from students.models import Enrollment, Student
from tenancy.context import school_context
from tenancy.models import School

from .models import AttendanceRecord


class TwoStudentRegisterTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="North School", slug="north", email="north@example.test")
        self.admin = User.objects.create_user(
            email="admin@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.SCHOOL_ADMIN,
        )
        with school_context(self.school):
            self.term = AcademicTerm.objects.create(
                name="Term 1", start_date="2026-01-10", end_date="2026-04-10", is_current=True
            )
            self.school_class = SchoolClass.objects.create(name="Grade 6", level=6)
            self.first = Student.objects.create(
                admission_number="A-1", first_name="Ada", last_name="Lovelace"
            )
            self.second = Student.objects.create(
                admission_number="A-2", first_name="Grace", last_name="Hopper"
            )
            Enrollment.objects.create(student=self.first, school_class=self.school_class, term=self.term)
            Enrollment.objects.create(student=self.second, school_class=self.school_class, term=self.term)

    def test_register_lists_both_students(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("attendance:register"),
            {"school_class": self.school_class.pk, "term": self.term.pk, "date": "2026-02-03"},
        )
        self.assertContains(response, "Lovelace")
        self.assertContains(response, "Hopper")

    def test_both_students_are_saved_and_shown(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("attendance:register"),
            {
                "action": "save",
                "school_class": self.school_class.pk,
                "term": self.term.pk,
                "date": "2026-02-03",
                f"status_{self.first.pk}": AttendanceRecord.Status.PRESENT,
                f"status_{self.second.pk}": AttendanceRecord.Status.ABSENT,
            },
        )
        self.assertEqual(response.status_code, 302)
        with school_context(self.school):
            self.assertEqual(AttendanceRecord.objects.count(), 2)

        listing = self.client.get(reverse("attendance:record_list"))
        self.assertContains(listing, "Lovelace")
        self.assertContains(listing, "Hopper")

    def test_not_enrolled_student_is_offered_but_not_in_the_register(self):
        with school_context(self.school):
            alan = Student.objects.create(
                admission_number="A-3", first_name="Alan", last_name="Turing"
            )
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("attendance:register"),
            {"school_class": self.school_class.pk, "term": self.term.pk},
        )
        # Offered so they can be enrolled...
        self.assertContains(response, "Turing")
        # ...but has no attendance row yet.
        self.assertNotContains(response, f"status_{alan.pk}")

    def test_enrolling_from_the_register_adds_the_student(self):
        with school_context(self.school):
            alan = Student.objects.create(
                admission_number="A-3", first_name="Alan", last_name="Turing"
            )
        self.client.force_login(self.admin)
        page = self.client.get(
            reverse("attendance:register"),
            {"school_class": self.school_class.pk, "term": self.term.pk},
        )
        self.assertContains(page, "Not enrolled for")

        response = self.client.post(
            reverse("attendance:register"),
            {
                "action": "enroll",
                "student": alan.pk,
                "school_class": self.school_class.pk,
                "term": self.term.pk,
                "date": "2026-02-03",
            },
        )
        self.assertEqual(response.status_code, 302)
        with school_context(self.school):
            self.assertTrue(Enrollment.objects.filter(student=alan, term=self.term).exists())

        reloaded = self.client.get(
            reverse("attendance:register"),
            {"school_class": self.school_class.pk, "term": self.term.pk},
        )
        self.assertContains(reloaded, "Turing")

    def test_student_in_another_class_is_flagged(self):
        with school_context(self.school):
            other_class = SchoolClass.objects.create(name="Grade 7", level=7)
            Enrollment.objects.filter(student=self.second).update(school_class=other_class)
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("attendance:register"),
            {"school_class": self.school_class.pk, "term": self.term.pk},
        )
        self.assertContains(response, "Enrolled in other classes this term")
        self.assertContains(response, "Hopper")

    def test_all_classes_mode_lists_and_saves_every_student(self):
        with school_context(self.school):
            other_class = SchoolClass.objects.create(name="Grade 7", level=7)
            Enrollment.objects.filter(student=self.second).update(school_class=other_class)
        self.client.force_login(self.admin)

        page = self.client.get(
            reverse("attendance:register"), {"school_class": "all", "term": self.term.pk}
        )
        self.assertContains(page, "Lovelace")
        self.assertContains(page, "Hopper")

        response = self.client.post(
            reverse("attendance:register"),
            {
                "action": "save",
                "school_class": "all",
                "term": self.term.pk,
                "date": "2026-02-05",
                f"status_{self.first.pk}": AttendanceRecord.Status.PRESENT,
                f"status_{self.second.pk}": AttendanceRecord.Status.ABSENT,
            },
        )
        self.assertEqual(response.status_code, 302)
        with school_context(self.school):
            self.assertEqual(AttendanceRecord.objects.filter(date="2026-02-05").count(), 2)
