import logging

from celery import shared_task

from .services import purge_expired

logger = logging.getLogger(__name__)


@shared_task
def purge_expired_announcements():
    """Scheduled housekeeping: remove announcements whose expiry has passed."""
    deleted = purge_expired()
    if deleted:
        logger.info("Purged %s expired announcement(s)", deleted)
    return deleted
