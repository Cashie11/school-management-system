from decimal import Decimal

from django.test import TestCase

from academics.models import AcademicTerm, ClassSubject, SchoolClass, Subject
from students.models import Student
from tenancy.context import school_context
from tenancy.models import School

from .models import Assessment, Score


class ResultsIsolationTests(TestCase):
    def setUp(self):
        self.school_a = School.objects.create(name="North School", slug="north", email="north@example.test")
        self.school_b = School.objects.create(name="South School", slug="south", email="south@example.test")

    def _fixture(self):
        term = AcademicTerm.objects.create(
            name="Term 1", start_date="2026-01-10", end_date="2026-04-10", is_current=True
        )
        school_class = SchoolClass.objects.create(name="Grade 7", level=7)
        subject = Subject.objects.create(name="Mathematics")
        class_subject = ClassSubject.objects.create(school_class=school_class, subject=subject)
        student = Student.objects.create(admission_number="A-1", first_name="Ada", last_name="Lovelace")
        return term, class_subject, student

    def test_scores_and_assessments_are_scoped(self):
        with school_context(self.school_a):
            term, class_subject, student = self._fixture()
            assessment = Assessment.objects.create(
                class_subject=class_subject, term=term, name="Midterm", max_score=50
            )
            score = Score.objects.create(assessment=assessment, student=student, value=Decimal("40"))
            self.assertEqual(score.percentage, Decimal("80.00"))

        with school_context(self.school_b):
            self.assertEqual(Assessment.objects.count(), 0)
            self.assertEqual(Score.objects.count(), 0)
            self.assertEqual(Student.objects.count(), 0)

    def test_score_cannot_be_written_across_schools(self):
        with school_context(self.school_a):
            term, class_subject, student = self._fixture()
            assessment = Assessment.objects.create(
                class_subject=class_subject, term=term, name="Midterm", max_score=50
            )

        with school_context(self.school_b):
            score = Score(school=self.school_a, assessment=assessment, student=student, value=Decimal("10"))
            with self.assertRaises(ValueError):
                score.save()

    def test_percentage_handles_missing_value(self):
        with school_context(self.school_a):
            term, class_subject, student = self._fixture()
            assessment = Assessment.objects.create(
                class_subject=class_subject, term=term, name="Quiz", max_score=25
            )
            score = Score.objects.create(assessment=assessment, student=student)
            self.assertIsNone(score.percentage)
