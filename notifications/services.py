"""Student notification emails.

Rendering, sending and logging happen here. The public ``notify_*`` helpers
queue a Celery task and return how many recipients were queued, so a slow mail
server never holds up the request that triggered the notification.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from .models import EmailLog

logger = logging.getLogger(__name__)


def student_recipients(student):
    """The student's own address, plus every linked guardian."""
    emails = []
    if student.email:
        emails.append(student.email)
    for guardian in student.guardians.select_related("user"):
        email = guardian.user.email
        if email and email not in emails:
            emails.append(email)
    return emails


def deliver(*, kind, subject, recipients, template, context, student=None):
    """Render and send one notification. Never raises: a mail problem must not
    break the request or the task that triggered it.

    The caller is responsible for having the right school in context.
    """
    if not recipients:
        return []

    try:
        context = {**context, "subject": subject}
        text_body = render_to_string(f"notifications/{template}.txt", context)
        html_body = render_to_string(f"notifications/{template}.html", context)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to render the %s notification", kind)
        return []

    logs = []
    for recipient in recipients:
        try:
            message = EmailMultiAlternatives(
                subject, text_body, settings.DEFAULT_FROM_EMAIL, [recipient]
            )
            message.attach_alternative(html_body, "text/html")
            message.send(fail_silently=False)
            logs.append(
                EmailLog.objects.create(
                    kind=kind, to_email=recipient, subject=subject[:200], student=student
                )
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to send the %s notification to %s", kind, recipient)
            continue
    return logs


# Queued notifications -----------------------------------------------------
# Each helper queues work and returns the number of recipients it queued for.


def notify_student_welcome(student):
    from .tasks import send_student_welcome

    recipients = student_recipients(student)
    if recipients:
        send_student_welcome.delay(student.pk)
    return len(recipients)


def notify_account_welcome(user):
    from .tasks import send_account_welcome

    if not user.email:
        return 0
    send_account_welcome.delay(user.pk)
    return 1


def notify_guardian_linked(guardian):
    from .tasks import send_guardian_linked

    if not guardian.user.email:
        return 0
    send_guardian_linked.delay(guardian.pk)
    return 1


def notify_enrollment(enrollment):
    from .tasks import send_enrollment

    recipients = student_recipients(enrollment.student)
    if recipients:
        send_enrollment.delay(enrollment.pk)
    return len(recipients)


def notify_absence(record):
    from .tasks import send_absence

    recipients = student_recipients(record.student)
    if recipients:
        send_absence.delay(record.pk)
    return len(recipients)


def notify_assessment_published(assessment):
    from students.models import Enrollment

    from .tasks import send_assessment_published

    enrollments = Enrollment.objects.filter(
        school_class=assessment.class_subject.school_class, term=assessment.term
    ).select_related("student")
    queued = 0
    for enrollment in enrollments:
        if student_recipients(enrollment.student):
            send_assessment_published.delay(assessment.pk, enrollment.student_id)
            queued += 1
    return queued


def notify_assessment_result(submission):
    from .tasks import send_assessment_result

    recipients = student_recipients(submission.student)
    if recipients:
        send_assessment_result.delay(submission.pk)
    return len(recipients)


def notify_results(student, report, position=None, class_size=None):
    from .tasks import send_results

    recipients = student_recipients(student)
    if recipients:
        send_results.delay(student.pk, report["term"].pk, position, class_size)
    return len(recipients)


def notify_discipline(record):
    from .tasks import send_discipline

    recipients = student_recipients(record.student)
    if recipients:
        send_discipline.delay(record.pk)
    return len(recipients)
