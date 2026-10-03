"""Queuing the support email.

Rendering and sending happen in a Celery task so a slow mail server never holds
up the request that submitted the form. Without a broker the task runs inline.
"""


def queue_support_message(message):
    from .tasks import send_support_message

    send_support_message.delay(message.pk)
    return 1
