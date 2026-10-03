"""Announcement housekeeping."""

from django.utils import timezone

from .models import Announcement


def purge_expired():
    """Delete announcements whose expiry has passed. Returns how many went.

    Uses the unscoped manager because this runs from a background task or a
    management command, where there is no request and therefore no school in
    context. It is deliberate, and the only place outside the admin that reads
    across schools.
    """
    now = timezone.now()
    expired = Announcement.all_objects.filter(
        expires_at__isnull=False, expires_at__lte=now
    )
    deleted = expired.count()
    if deleted:
        expired.delete()
    return deleted
