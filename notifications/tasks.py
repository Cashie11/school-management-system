"""Background notification tasks.

These run in a Celery worker with no request in flight, so each one loads its
object with the unscoped manager and then sets the school context before
touching tenant data or writing the email log.
"""

from celery import shared_task

from academics.models import AcademicTerm
from accounts.models import User
from attendance.models import AttendanceRecord
from results.models import Assessment, Submission
from students.models import Enrollment, Guardian, Student
from tenancy.context import school_context

from .models import EmailLog
from .services import deliver, student_recipients

RETRY = {
    "bind": True,
    "autoretry_for": (Exception,),
    "retry_backoff": True,
    "retry_kwargs": {"max_retries": 3},
}


@shared_task(**RETRY)
def send_student_welcome(self, student_id):
    student = Student.all_objects.filter(pk=student_id).first()
    if student is None:
        return 0
    with school_context(student.school_id):
        logs = deliver(
            kind=EmailLog.Kind.WELCOME,
            subject=f"Welcome to {student.school.name}",
            recipients=student_recipients(student),
            template="welcome",
            context={"student": student, "school": student.school},
            student=student,
        )
    return len(logs)


@shared_task(**RETRY)
def send_account_welcome(self, user_id):
    user = User.objects.filter(pk=user_id).first()
    if user is None or user.school_id is None:
        return 0
    with school_context(user.school_id):
        logs = deliver(
            kind=EmailLog.Kind.ACCOUNT,
            subject=f"Your {user.school.name} account",
            recipients=[user.email],
            template="account_welcome",
            context={"user": user, "school": user.school, "role": user.get_role_display()},
        )
    return len(logs)


@shared_task(**RETRY)
def send_guardian_linked(self, guardian_id):
    guardian = (
        Guardian.all_objects.select_related("user", "student").filter(pk=guardian_id).first()
    )
    if guardian is None:
        return 0
    with school_context(guardian.school_id):
        logs = deliver(
            kind=EmailLog.Kind.GUARDIAN_LINK,
            subject=f"You are now linked to {guardian.student.full_name}",
            recipients=[guardian.user.email],
            template="guardian_link",
            context={
                "guardian": guardian,
                "student": guardian.student,
                "school": guardian.school,
            },
            student=guardian.student,
        )
    return len(logs)


@shared_task(**RETRY)
def send_enrollment(self, enrollment_id):
    enrollment = (
        Enrollment.all_objects.select_related("student", "school_class", "term")
        .filter(pk=enrollment_id)
        .first()
    )
    if enrollment is None:
        return 0
    student = enrollment.student
    with school_context(enrollment.school_id):
        logs = deliver(
            kind=EmailLog.Kind.ENROLLMENT,
            subject=f"{student.full_name} enrolled in {enrollment.school_class}",
            recipients=student_recipients(student),
            template="enrollment",
            context={"student": student, "school": student.school, "enrollment": enrollment},
            student=student,
        )
    return len(logs)


@shared_task(**RETRY)
def send_absence(self, record_id):
    record = AttendanceRecord.all_objects.select_related("student").filter(pk=record_id).first()
    if record is None:
        return 0
    student = record.student
    with school_context(record.school_id):
        logs = deliver(
            kind=EmailLog.Kind.ABSENCE,
            subject=f"Absence recorded for {student.full_name}",
            recipients=student_recipients(student),
            template="absence",
            context={"student": student, "school": student.school, "record": record},
            student=student,
        )
    return len(logs)


@shared_task(**RETRY)
def send_assessment_published(self, assessment_id, student_id):
    assessment = (
        Assessment.all_objects.select_related("class_subject__subject", "term")
        .filter(pk=assessment_id)
        .first()
    )
    student = Student.all_objects.filter(pk=student_id).first()
    if assessment is None or student is None:
        return 0
    with school_context(assessment.school_id):
        logs = deliver(
            kind=EmailLog.Kind.ASSESSMENT,
            subject=f"New assessment: {assessment.name}",
            recipients=student_recipients(student),
            template="assessment_published",
            context={"student": student, "school": student.school, "assessment": assessment},
            student=student,
        )
    return len(logs)


@shared_task(**RETRY)
def send_assessment_result(self, submission_id):
    submission = (
        Submission.all_objects.select_related("assessment", "student")
        .filter(pk=submission_id)
        .first()
    )
    if submission is None:
        return 0
    student = submission.student
    with school_context(submission.school_id):
        logs = deliver(
            kind=EmailLog.Kind.RESULTS,
            subject=f"{submission.assessment.name}: result ready for {student.full_name}",
            recipients=student_recipients(student),
            template="assessment_result",
            context={
                "student": student,
                "school": student.school,
                "assessment": submission.assessment,
                "submission": submission,
            },
            student=student,
        )
    return len(logs)


@shared_task(**RETRY)
def send_results(self, student_id, term_id, position=None, class_size=None):
    from results.services import student_term_report

    student = Student.all_objects.filter(pk=student_id).first()
    term = AcademicTerm.all_objects.filter(pk=term_id).first()
    if student is None or term is None:
        return 0
    with school_context(student.school_id):
        report = student_term_report(student, term)
        logs = deliver(
            kind=EmailLog.Kind.RESULTS,
            subject=f"Results for {term.name} - {student.full_name}",
            recipients=student_recipients(student),
            template="results",
            context={
                "student": student,
                "school": student.school,
                "report": report,
                "position": position,
                "class_size": class_size,
            },
            student=student,
        )
    return len(logs)


@shared_task(**RETRY)
def send_discipline(self, record_id):
    from students.models import DisciplineRecord

    record = (
        DisciplineRecord.all_objects.select_related("student").filter(pk=record_id).first()
    )
    if record is None:
        return 0
    with school_context(record.school_id):
        logs = deliver(
            kind=EmailLog.Kind.DISCIPLINE,
            subject=f"{record.get_kind_display()} notice - {record.student.full_name}",
            recipients=student_recipients(record.student),
            template="discipline",
            context={"record": record, "student": record.student, "school": record.school},
            student=record.student,
        )
    return len(logs)
