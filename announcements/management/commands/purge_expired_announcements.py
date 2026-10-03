from django.core.management.base import BaseCommand

from announcements.services import purge_expired


class Command(BaseCommand):
    help = "Delete announcements whose expiry date has passed."

    def handle(self, *args, **options):
        deleted = purge_expired()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} expired announcement(s)."))
