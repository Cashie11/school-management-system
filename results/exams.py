"""Online assessment logic: availability, auto-marking and score sync."""

from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from notifications.services import notify_assessment_result
from students.models import Enrollment

from .models import Assessment, Question, Score, Submission


def online_assessments_for(student):
    """Online assessments for every class and term the student is enrolled in."""
    enrollments = list(Enrollment.objects.filter(student=student))
    if not enrollments:
        return Assessment.objects.none()
    conditions = Q()
    for enrollment in enrollments:
        conditions |= Q(
            class_subject__school_class_id=enrollment.school_class_id,
            term_id=enrollment.term_id,
        )
    return Assessment.objects.filter(conditions, mode=Assessment.Mode.ONLINE).select_related(
        "class_subject__subject", "class_subject__school_class", "term"
    )


def mark_objective_answers(submission):
    """Award points for objective answers and record the objective score."""
    total = Decimal("0")
    answers = submission.answers.select_related("question", "selected_choice")
    for answer in answers:
        question = answer.question
        if not question.is_objective:
            continue
        if answer.selected_choice_id and answer.selected_choice.is_correct:
            answer.awarded_points = question.points
            total += question.points
        else:
            answer.awarded_points = Decimal("0")
        answer.save(update_fields=["awarded_points"])
    submission.objective_score = total
    return total


def sync_score(submission):
    """Write the submission total onto the assessment's Score record."""
    score, _ = Score.objects.update_or_create(
        assessment=submission.assessment,
        student=submission.student,
        defaults={"value": submission.total_score},
    )
    return score


def finalize_submission(submission, now=None):
    """Settle a submitted attempt: mark it complete when no theory marking is pending."""
    assessment = submission.assessment
    was_marked = submission.status == Submission.Status.MARKED
    theory_answers = list(
        submission.answers.filter(question__section=Question.Section.THEORY)
    )
    has_theory = assessment.questions.filter(section=Question.Section.THEORY).exists()

    if has_theory:
        pending = any(answer.awarded_points is None for answer in theory_answers)
    else:
        pending = False

    if pending:
        submission.theory_score = None
        submission.status = Submission.Status.SUBMITTED
    else:
        theory_total = sum(
            (answer.awarded_points or Decimal("0")) for answer in theory_answers
        )
        submission.theory_score = theory_total
        submission.status = Submission.Status.MARKED

    if submission.submitted_at is None:
        submission.submitted_at = now or timezone.now()
    submission.save()

    if submission.status == Submission.Status.MARKED:
        sync_score(submission)
        if not was_marked:
            notify_assessment_result(submission)
    return submission
