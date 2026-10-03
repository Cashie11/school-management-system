from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from academics.models import AcademicTerm, ClassSubject, SchoolClass, Subject
from accounts.models import User
from students.models import Enrollment, Guardian, Student
from tenancy.context import school_context
from tenancy.models import School

from .models import Assessment, Choice, Question, Score, Submission


class OnlineExamTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="North School", slug="north", email="north@example.test")
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
            self.school_class = SchoolClass.objects.create(name="Grade 6", level=6)
            self.subject = Subject.objects.create(name="Mathematics")
            self.class_subject = ClassSubject.objects.create(
                school_class=self.school_class, subject=self.subject, teacher=self.teacher
            )
            self.student = Student.objects.create(
                admission_number="A-1", first_name="Ada", last_name="Lovelace"
            )
            Enrollment.objects.create(
                student=self.student, school_class=self.school_class, term=self.term
            )
            Guardian.objects.create(user=self.parent, student=self.student, is_primary=True)
            self.assessment = Assessment.objects.create(
                class_subject=self.class_subject,
                term=self.term,
                name="Quiz",
                mode=Assessment.Mode.ONLINE,
                max_score=0,
            )

    def _add_objective_question(self, points="10"):
        self.client.force_login(self.teacher)
        self.client.post(
            reverse("results:question_create", args=[self.assessment.pk]),
            {"section": Question.Section.OBJECTIVE, "text": "2 + 2 = ?", "points": points, "order": 1},
        )
        with school_context(self.school):
            question = Question.objects.get(text="2 + 2 = ?")
        self.client.post(
            reverse("results:choice_create", args=[question.pk]),
            {"text": "4", "is_correct": "on", "order": 1},
        )
        self.client.post(
            reverse("results:choice_create", args=[question.pk]),
            {"text": "5", "order": 2},
        )
        with school_context(self.school):
            correct = Choice.objects.get(text="4")
        return question, correct

    def _publish(self):
        self.client.force_login(self.teacher)
        self.client.post(reverse("results:assessment_publish", args=[self.assessment.pk]))

    def test_question_added_and_max_score_synced(self):
        self._add_objective_question(points="10")
        with school_context(self.school):
            self.assertEqual(Question.objects.count(), 1)
            refreshed = Assessment.objects.get(pk=self.assessment.pk)
            self.assertEqual(refreshed.max_score, Decimal("10.00"))
            self.assertEqual(Choice.objects.count(), 2)

    def test_student_objective_attempt_is_auto_marked(self):
        question, correct = self._add_objective_question()
        self._publish()

        self.client.force_login(self.parent)
        listing = self.client.get(reverse("portal:student_exams", args=[self.student.pk]))
        self.assertContains(listing, "Quiz")

        self.client.post(
            reverse("portal:exam_take", args=[self.student.pk, self.assessment.pk]),
            {f"choice_{question.pk}": correct.pk},
        )
        with school_context(self.school):
            submission = Submission.objects.get()
            self.assertEqual(submission.status, Submission.Status.MARKED)
            self.assertEqual(submission.objective_score, Decimal("10.00"))
            self.assertEqual(Score.objects.get().value, Decimal("10.00"))

    def test_wrong_objective_answer_scores_zero(self):
        question, _correct = self._add_objective_question()
        self._publish()
        with school_context(self.school):
            wrong = Choice.objects.get(text="5")
        self.client.force_login(self.parent)
        self.client.post(
            reverse("portal:exam_take", args=[self.student.pk, self.assessment.pk]),
            {f"choice_{question.pk}": wrong.pk},
        )
        with school_context(self.school):
            self.assertEqual(Submission.objects.get().objective_score, Decimal("0.00"))

    def test_theory_answer_waits_for_teacher_marking(self):
        self._add_objective_question(points="10")
        self.client.force_login(self.teacher)
        self.client.post(
            reverse("results:question_create", args=[self.assessment.pk]),
            {"section": Question.Section.THEORY, "text": "Explain addition.", "points": "5", "order": 1},
        )
        self._publish()

        with school_context(self.school):
            objective = Question.objects.get(section=Question.Section.OBJECTIVE)
            objective_choice = Choice.objects.get(question=objective, is_correct=True)
            theory = Question.objects.get(section=Question.Section.THEORY)

        self.client.force_login(self.parent)
        self.client.post(
            reverse("portal:exam_take", args=[self.student.pk, self.assessment.pk]),
            {
                f"choice_{objective.pk}": objective_choice.pk,
                f"text_{theory.pk}": "Adding two numbers gives their sum.",
            },
        )
        with school_context(self.school):
            submission = Submission.objects.get()
            self.assertEqual(submission.status, Submission.Status.SUBMITTED)
            self.assertEqual(Score.objects.count(), 0)

        # Teacher marks the theory answer.
        self.client.force_login(self.teacher)
        with school_context(self.school):
            answer = submission.answers.get(question=theory)
        self.client.post(
            reverse("results:submission_mark", args=[submission.pk]),
            {f"points_{answer.pk}": "4"},
        )
        with school_context(self.school):
            submission.refresh_from_db()
            self.assertEqual(submission.status, Submission.Status.MARKED)
            self.assertEqual(submission.total_score, Decimal("14.00"))
            self.assertEqual(Score.objects.get().value, Decimal("14.00"))

    def test_one_attempt_only(self):
        question, correct = self._add_objective_question()
        self._publish()
        self.client.force_login(self.parent)
        url = reverse("portal:exam_take", args=[self.student.pk, self.assessment.pk])
        self.client.post(url, {f"choice_{question.pk}": correct.pk})
        self.client.post(url, {f"choice_{question.pk}": correct.pk})
        with school_context(self.school):
            self.assertEqual(Submission.objects.count(), 1)

    def test_teacher_can_reset_an_attempt(self):
        question, correct = self._add_objective_question()
        self._publish()
        self.client.force_login(self.parent)
        self.client.post(
            reverse("portal:exam_take", args=[self.student.pk, self.assessment.pk]),
            {f"choice_{question.pk}": correct.pk},
        )
        with school_context(self.school):
            submission = Submission.objects.get()
        self.client.force_login(self.teacher)
        self.client.post(reverse("results:submission_reset", args=[submission.pk]))
        with school_context(self.school):
            self.assertEqual(Submission.objects.count(), 0)
            self.assertEqual(Score.objects.count(), 0)

    def test_closed_assessment_blocks_the_student(self):
        self._add_objective_question()
        with school_context(self.school):
            self.assessment.available_from = timezone.now() + timezone.timedelta(days=1)
            self.assessment.save(update_fields=["available_from"])
        self._publish()
        self.client.force_login(self.parent)
        response = self.client.get(
            reverse("portal:exam_take", args=[self.student.pk, self.assessment.pk])
        )
        self.assertEqual(response.status_code, 302)

    def test_parent_cannot_open_another_familys_student(self):
        with school_context(self.school):
            stranger = Student.objects.create(
                admission_number="A-9", first_name="Alan", last_name="Turing"
            )
        self.client.force_login(self.parent)
        response = self.client.get(reverse("portal:student_exams", args=[stranger.pk]))
        self.assertEqual(response.status_code, 404)

    def test_teacher_cannot_author_another_teachers_assessment(self):
        other_teacher = User.objects.create_user(
            email="teacher2@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.TEACHER,
        )
        self.client.force_login(other_teacher)
        response = self.client.get(
            reverse("results:assessment_questions", args=[self.assessment.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_questions_lock_once_a_student_has_answered(self):
        question, correct = self._add_objective_question()
        self._publish()
        self.client.force_login(self.parent)
        self.client.post(
            reverse("portal:exam_take", args=[self.student.pk, self.assessment.pk]),
            {f"choice_{question.pk}": correct.pk},
        )

        self.client.force_login(self.teacher)
        response = self.client.get(reverse("results:question_delete", args=[question.pk]))
        self.assertEqual(response.status_code, 302)
        with school_context(self.school):
            self.assertTrue(Question.objects.filter(pk=question.pk).exists())

        page = self.client.get(
            reverse("results:assessment_questions", args=[self.assessment.pk])
        )
        self.assertContains(page, "locked")
