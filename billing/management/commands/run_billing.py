from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction
from django.utils import timezone

from billing.services import generate_invoice, next_period_date
from subscriptions.models import Subscription


class Command(BaseCommand):
    help = 'Generate invoices for subscriptions due on or before today.'

    def handle(self, *args, **options):
        today = timezone.localdate()
        billed = 0
        closed = 0
        due_subscriptions = Subscription.objects.select_related('plan').filter(
            status='active', next_billing_date__lte=today
        )
        for subscription in due_subscriptions.iterator():
            with transaction.atomic():
                subscription = Subscription.objects.select_for_update().select_related('plan').get(pk=subscription.pk)
                if subscription.expiry_date and subscription.expiry_date < today and subscription.plan.auto_close:
                    subscription.transition_to('closed')
                    closed += 1
                    continue
                period_start = subscription.next_billing_date
                try:
                    invoice = generate_invoice(subscription, period_start=period_start)
                except IntegrityError:
                    invoice = None
                if invoice:
                    billed += 1
                subscription.next_billing_date = next_period_date(subscription.plan, period_start)
                subscription.save(update_fields=['next_billing_date', 'updated_at'])
        self.stdout.write(self.style.SUCCESS(f'Billing complete: {billed} invoice(s) generated, {closed} subscription(s) closed.'))
