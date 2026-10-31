from celery import shared_task

from .metrics import refresh_daily_snapshot


@shared_task
def refresh_daily_metric_snapshot():
    snapshot = refresh_daily_snapshot()
    return snapshot.snapshot_date.isoformat()
