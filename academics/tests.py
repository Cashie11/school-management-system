from django.db import IntegrityError, transaction
from django.test import TestCase

from tenancy.context import school_context
from tenancy.models import School

from .models import AcademicTerm, ClassSubject, SchoolClass, Subject


class AcademicsIsolationTests(TestCase):
    def setUp(self):
        self.school_a = School.objects.create(name="North School", slug="north", email="north@example.test")
        self.school_b = School.objects.create(name="South School", slug="south", email="south@example.test")

    def test_records_are_scoped_to_the_active_school(self):
        with school_context(self.school_a):
            AcademicTerm.objects.create(
                name="Term 1", start_date="2026-01-10", end_date="2026-04-10", is_current=True
            )
            Subject.objects.create(name="Mathematics")

        with school_context(self.school_b):
            self.assertEqual(AcademicTerm.objects.count(), 0)
            self.assertEqual(Subject.objects.count(), 0)

        # With no active school nothing is visible.
        self.assertEqual(AcademicTerm.objects.count(), 0)
        self.assertEqual(Subject.objects.count(), 0)

    def test_related_access_is_scoped(self):
        with school_context(self.school_a):
            subject = Subject.objects.create(name="Science")
            school_class = SchoolClass.objects.create(name="Grade 7", level=7)
            ClassSubject.objects.create(school_class=school_class, subject=subject)

        with school_context(self.school_b):
            # Related managers use the scoped base manager, so another school's
            # rows stay invisible.
            self.assertEqual(self.school_a.classsubject_set.count(), 0)

        with school_context(self.school_a):
            self.assertEqual(self.school_a.classsubject_set.count(), 1)

    def test_subject_names_are_unique_per_school(self):
        with school_context(self.school_a):
            Subject.objects.create(name="History")
            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    Subject.objects.create(name="History")

        # The same name is allowed in a different school.
        with school_context(self.school_b):
            Subject.objects.create(name="History")
            self.assertEqual(Subject.objects.count(), 1)

    def test_only_one_current_term_per_school(self):
        with school_context(self.school_a):
            AcademicTerm.objects.create(
                name="Term 1", start_date="2026-01-10", end_date="2026-04-10", is_current=True
            )
            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    AcademicTerm.objects.create(
                        name="Term 2", start_date="2026-04-20", end_date="2026-08-10", is_current=True
                    )

    def test_teacher_assignment_is_scoped(self):
        from accounts.models import User

        teacher = User.objects.create_user(
            email="teacher@north.example.test",
            password="a-strong-test-password",
            school=self.school_a,
            role=User.Role.TEACHER,
        )
        with school_context(self.school_a):
            subject = Subject.objects.create(name="English")
            school_class = SchoolClass.objects.create(name="Grade 8", level=8)
            assignment = ClassSubject.objects.create(
                school_class=school_class, subject=subject, teacher=teacher
            )
            self.assertEqual(assignment.teacher, teacher)
            self.assertEqual(teacher.class_subjects.count(), 1)
