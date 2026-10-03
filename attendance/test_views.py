from django.test import TestCase
from django.urls import reverse

from academics.models import AcademicTerm, ClassSubject, SchoolClass, Subject
from accounts.models import User
from students.models import Enrollment, Student
from tenancy.context import school_context
from tenancy.models import School

from .models import AttendanceRecord


class AttendanceViewTests(TestCase):
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
        self.parent = User.objects.create_user(
            email="parent@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.PARENT_STUDENT,
        )
        with school_context(self.school):
            self.term = AcademicTerm.objects.create(
                name="Term 1", start_date="2026-01-10", end_date="2026-04-10", is_current=True
            )
            self.assigned = SchoolClass.objects.create(name="Grade 6", level=6)
            self.unassigned = SchoolClass.objects.create(name="Grade 7", level=7)
            subject = Subject.objects.create(name="Mathematics")
            ClassSubject.objects.create(
                school_class=self.assigned, subject=subject, teacher=self.teacher
            )
            self.student = Student.objects.create(
                admission_number="A-1", first_name="Ada", last_name="Lovelace"
            )
            Enrollment.objects.create(student=self.student, school_class=self.assigned, term=self.term)

    def test_parent_cannot_access_attendance(self):
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get(reverse("attendance:register")).status_code, 403)

    def test_teacher_marks_attendance(self):
        self.client.force_login(self.teacher)
        response = self.client.post(
            reverse("attendance:register"),
            {
                "action": "save",
                "school_class": self.assigned.pk,
                "term": self.term.pk,
                "date": "2026-02-03",
                f"status_{self.student.pk}": AttendanceRecord.Status.ABSENT,
                f"note_{self.student.pk}": "Sick",
            },
        )
        self.assertEqual(response.status_code, 302)
        with school_context(self.school):
            record = AttendanceRecord.objects.get()
        self.assertEqual(record.status, AttendanceRecord.Status.ABSENT)
        self.assertEqual(record.note, "Sick")
        self.assertEqual(record.recorded_by, self.teacher)

    def test_teacher_only_sees_assigned_classes(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("attendance:register"))
        self.assertContains(response, "Grade 6")
        self.assertNotContains(response, "Grade 7")

    def test_attendance_is_updated_not_duplicated(self):
        self.client.force_login(self.admin)
        payload = {
            "action": "save",
            "school_class": self.assigned.pk,
            "term": self.term.pk,
            "date": "2026-02-03",
            f"status_{self.student.pk}": AttendanceRecord.Status.PRESENT,
        }
        self.client.post(reverse("attendance:register"), payload)
        payload[f"status_{self.student.pk}"] = AttendanceRecord.Status.LATE
        self.client.post(reverse("attendance:register"), payload)
        with school_context(self.school):
            self.assertEqual(AttendanceRecord.objects.count(), 1)
            self.assertEqual(AttendanceRecord.objects.get().status, AttendanceRecord.Status.LATE)

    def test_register_only_lists_enrolled_students(self):
        with school_context(self.school):
            hopper = Student.objects.create(
                admission_number="A-2", first_name="Grace", last_name="Hopper"
            )
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("attendance:register"),
            {"school_class": self.assigned.pk, "term": self.term.pk},
        )
        # The enrolled student has a register row; the other student does not.
        self.assertContains(response, f"status_{self.student.pk}")
        self.assertNotContains(response, f"status_{hopper.pk}")

    def test_another_schools_class_is_never_selected(self):
        with school_context(self.other):
            other_class = SchoolClass.objects.create(name="Grade 9", level=9)
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("attendance:register"), {"school_class": other_class.pk}
        )
        self.assertNotContains(response, "Grade 9")

    def test_records_view_lists_own_school_only(self):
        with school_context(self.school):
            AttendanceRecord.objects.create(
                student=self.student,
                term=self.term,
                date="2026-02-03",
                status=AttendanceRecord.Status.PRESENT,
            )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("attendance:record_list"))
        self.assertContains(response, "Lovelace")
        self.assertContains(response, "Present")
