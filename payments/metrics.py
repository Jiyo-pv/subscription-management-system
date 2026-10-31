from django.db.models import F, Sum
from django.utils import timezone

from billing.models import Invoice
from subscriptions.models import Subscription

from .models import DailyMetricSnapshot


def refresh_daily_snapshot(snapshot_date=None):
    snapshot_date = snapshot_date or timezone.localdate()
    open_invoices = Invoice.objects.filter(status=Invoice.OPEN)
    overdue_invoices = open_invoices.filter(due_date__lt=snapshot_date)
    paid_revenue = Invoice.objects.filter(
        status=Invoice.PAID,
    ).aggregate(total=Sum('amount_paid'))['total'] or 0

    snapshot, _ = DailyMetricSnapshot.objects.update_or_create(
        snapshot_date=snapshot_date,
        defaults={
            'active_subscriptions': Subscription.objects.filter(status='active').count(),
            'revenue': paid_revenue,
            'outstanding': open_invoices.annotate(
                balance=F('total_amount') - F('amount_paid'),
            ).aggregate(total=Sum('balance'))['total'] or 0,
            'overdue': overdue_invoices.annotate(
                balance=F('total_amount') - F('amount_paid'),
            ).aggregate(total=Sum('balance'))['total'] or 0,
            'overdue_invoice_count': overdue_invoices.count(),
        },
    )
    return snapshot
