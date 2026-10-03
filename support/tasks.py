"""Background delivery of support requests.

The task reloads the message by id, renders the email and sends it to the
support address. Failures are logged and retried; the message itself is already
stored, so a mail outage never loses a request.
"""

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from .models import SupportMessage

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_support_message(self, message_id):
    message = SupportMessage.objects.filter(pk=message_id).first()
    if message is None:
        return 0

    context = {"message": message}
    try:
        text_body = render_to_string("support/emails/support_request.txt", context)
        html_body = render_to_string("support/emails/support_request.html", context)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to render the support request email")
        return 0

    email = EmailMultiAlternatives(
        subject=f"[Support] {message.subject}",
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.SUPPORT_EMAIL],
        reply_to=[message.email],
    )
    email.attach_alternative(html_body, "text/html")
    email.send(fail_silently=False)
    return 1
