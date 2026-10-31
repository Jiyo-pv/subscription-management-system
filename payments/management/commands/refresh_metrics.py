from django.core.management.base import BaseCommand

from payments.metrics import refresh_daily_snapshot


class Command(BaseCommand):
    help = 'Refresh the daily payment and billing metric snapshot.'

    def handle(self, *args, **options):
        snapshot = refresh_daily_snapshot()
        self.stdout.write(
            self.style.SUCCESS(
                f'Refreshed metrics for {snapshot.snapshot_date}.'
            )
        )
