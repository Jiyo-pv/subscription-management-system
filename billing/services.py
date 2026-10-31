from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from .models import Invoice, InvoiceLine
from catalog.pricing import calculate_totals, consume_discount, get_applicable_discounts


def next_period_date(plan, start):
    increments = {'daily': timedelta(days=1), 'weekly': timedelta(weeks=1)}
    if plan.billing_period in increments:
        return start + increments[plan.billing_period]
    return start + relativedelta(months=1 if plan.billing_period == 'monthly' else 12)


@transaction.atomic
def generate_invoice(subscription, period_start=None, due_date=None, notes=''):
    """Idempotently bill one subscription period; returns None on a repeat run."""
    period_start = period_start or subscription.next_billing_date or timezone.localdate()
    due_date = due_date or timezone.localdate() + timedelta(days=15)
    period_end = next_period_date(subscription.plan, period_start) - timedelta(days=1)
    if Invoice.objects.filter(subscription=subscription, period_start=period_start).exists():
        return None
    source_lines = list(subscription.lines.all())
    if source_lines:
        line_data = [{'description': line.description, 'quantity': line.quantity, 'unit_price': line.unit_price + (line.variant.extra_price if line.variant_id else 0), 'tax_percent': line.tax.percent if line.tax_id and line.tax.is_active else 0} for line in source_lines]
    else:
        line_data = [{'description': f'{subscription.plan.name} subscription', 'quantity': subscription.plan.min_quantity, 'unit_price': subscription.plan.price, 'tax_percent': 0}]
    discounts = get_applicable_discounts(subscription)
    subtotal = sum((line['quantity'] * line['unit_price'] for line in line_data), 0)
    quantity = sum((line['quantity'] for line in line_data), 0)
    discounts = [discount for discount in discounts if subtotal >= discount.min_purchase and quantity >= discount.min_quantity]
    totals = calculate_totals(line_data, discounts)
    total_amount = totals.pop('total')
    invoice = Invoice.objects.create(
        subscription=subscription,
        customer=subscription.customer,
        period_start=period_start,
        period_end=period_end,
        due_date=due_date,
        status=Invoice.OPEN,
        notes=notes,
        **totals,
        total_amount=total_amount,
    )
    InvoiceLine.objects.bulk_create([
        InvoiceLine(invoice=invoice, description=line['description'], quantity=line['quantity'], unit_price=line['unit_price'], tax_percent=line['tax_percent'], amount=line['quantity'] * line['unit_price'])
        for line in line_data
    ])
    for discount in discounts:
        if not consume_discount(discount):
            continue
    return invoice


def create_invoice_for_subscription(subscription, due_date=None, notes=''):
    return generate_invoice(subscription, due_date=due_date, notes=notes)
