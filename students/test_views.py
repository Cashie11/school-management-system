from django.test import TestCase
from django.urls import reverse

from academics.models import AcademicTerm, ClassSubject, SchoolClass, Subject
from accounts.models import User
from tenancy.context import school_context
from tenancy.models import School

from .models import Enrollment, Student


class StudentViewTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="North School", slug="north", email="north@example.test")
        self.other = School.objects.create(name="South School", slug="south", email="south@example.test")
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
        self.parent = User.objects.create_user(
            email="parent@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.PARENT_STUDENT,
        )
        self.other_parent = User.objects.create_user(
            email="parent@south.example.test",
            password="a-strong-test-password",
            school=self.other,
            role=User.Role.PARENT_STUDENT,
        )

    def test_admin_creates_student(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("students:student_create"),
            {
                "admission_number": "A-100",
                "first_name": "Ada",
                "last_name": "Lovelace",
                "gender": "female",
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("students:student_list"))
        with school_context(self.school):
            student = Student.objects.get()
        self.assertEqual(student.school, self.school)

    def test_cross_tenant_student_is_hidden(self):
        with school_context(self.other):
            other_student = Student.objects.create(
                admission_number="B-1", first_name="Alan", last_name="Turing"
            )
        self.client.force_login(self.admin)
        detail = self.client.get(reverse("students:student_detail", args=[other_student.pk]))
        self.assertEqual(detail.status_code, 404)
        listing = self.client.get(reverse("students:student_list"))
        self.assertNotContains(listing, "Turing")

    def test_enrollment_cannot_repeat_for_the_same_term(self):
        with school_context(self.school):
            student = Student.objects.create(
                admission_number="A-1", first_name="Ada", last_name="Lovelace"
            )
        self.client.force_login(self.admin)
        payload = {
            "student": student.pk,
            "school_class": self.school_class.pk,
            "term": self.term.pk,
        }
        first = self.client.post(reverse("students:enrollment_create"), payload)
        self.assertRedirects(first, reverse("students:enrollment_list"))
        second = self.client.post(reverse("students:enrollment_create"), payload)
        self.assertEqual(second.status_code, 200)
        with school_context(self.school):
            self.assertEqual(Enrollment.objects.count(), 1)

    def test_guardian_dropdown_only_lists_own_school_parents(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("students:guardian_create"))
        self.assertContains(response, "parent@north.example.test")
        self.assertNotContains(response, "parent@south.example.test")

    def test_search_filters_students(self):
        with school_context(self.school):
            Student.objects.create(admission_number="A-1", first_name="Ada", last_name="Lovelace")
            Student.objects.create(admission_number="A-2", first_name="Grace", last_name="Hopper")
        self.client.force_login(self.admin)
        response = self.client.get(reverse("students:student_list"), {"q": "hopper"})
        self.assertContains(response, "Hopper")
        self.assertNotContains(response, "Lovelace")

    def test_student_detail_renders(self):
        with school_context(self.school):
            student = Student.objects.create(
                admission_number="A-1", first_name="Ada", last_name="Lovelace"
            )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("students:student_detail", args=[student.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lovelace")
        self.assertContains(response, "Attendance")

    def test_teacher_sees_only_students_in_their_classes(self):
        teacher = User.objects.create_user(
            email="teacher@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.TEACHER,
        )
        with school_context(self.school):
            subject = Subject.objects.create(name="Mathematics")
            ClassSubject.objects.create(
                school_class=self.school_class, subject=subject, teacher=teacher
            )
            mine = Student.objects.create(
                admission_number="A-1", first_name="Ada", last_name="Lovelace"
            )
            Enrollment.objects.create(student=mine, school_class=self.school_class, term=self.term)
            other_class = SchoolClass.objects.create(name="Grade 7", level=7)
            theirs = Student.objects.create(
                admission_number="B-1", first_name="Alan", last_name="Turing"
            )
            Enrollment.objects.create(student=theirs, school_class=other_class, term=self.term)

        self.client.force_login(teacher)
        listing = self.client.get(reverse("students:student_list"))
        self.assertContains(listing, "Lovelace")
        self.assertNotContains(listing, "Turing")
        self.assertNotContains(listing, "Add student")

        mine_detail = self.client.get(reverse("students:student_detail", args=[mine.pk]))
        self.assertEqual(mine_detail.status_code, 200)
        self.assertContains(mine_detail, "Lovelace")
        self.assertNotContains(mine_detail, "Link guardian")
        self.assertNotContains(mine_detail, "Enroll student")

        detail = self.client.get(reverse("students:student_detail", args=[theirs.pk]))
        self.assertEqual(detail.status_code, 404)

    def test_teacher_cannot_create_or_edit_students(self):
        teacher = User.objects.create_user(
            email="teacher2@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.TEACHER,
        )
        self.client.force_login(teacher)
        self.assertEqual(self.client.get(reverse("students:student_create")).status_code, 403)
