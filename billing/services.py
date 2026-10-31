from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import Invoice, InvoiceLine


@transaction.atomic
def create_invoice_for_subscription(subscription, due_date=None, notes=''):
    """Create an open invoice using the subscription's current lines or plan."""
    due_date = due_date or timezone.localdate() + timedelta(days=15)
    invoice = Invoice.objects.create(
        subscription=subscription,
        customer=subscription.customer,
        due_date=due_date,
        status=Invoice.OPEN,
        notes=notes,
    )
    lines = list(subscription.lines.all())
    if lines:
        InvoiceLine.objects.bulk_create([
            InvoiceLine(invoice=invoice, description=line.description, quantity=line.quantity, unit_price=line.unit_price)
            for line in lines
        ])
    else:
        InvoiceLine.objects.create(
            invoice=invoice,
            description=f'{subscription.plan.name} subscription',
            quantity=subscription.plan.min_quantity,
            unit_price=subscription.plan.price,
        )
    return invoice
