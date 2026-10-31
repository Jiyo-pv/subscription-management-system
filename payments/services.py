from django.core.exceptions import ValidationError
from django.db import transaction

from billing.models import Invoice

from .models import Payment


@transaction.atomic
def record_payment(invoice, method, amount, payment_date, note='', recorded_by=None):
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if invoice.status != Invoice.OPEN:
        raise ValidationError('Payments can only be recorded against an open invoice.')
    if amount <= 0:
        raise ValidationError('Payment amount must be greater than zero.')
    if amount > invoice.balance_due:
        raise ValidationError('Payment cannot exceed the outstanding balance.')
    payment = Payment.objects.create(invoice=invoice, method=method, amount=amount, payment_date=payment_date, note=note, recorded_by=recorded_by)
    invoice.amount_paid += amount
    if invoice.amount_paid == invoice.total_amount:
        invoice.mark_paid()
    else:
        invoice.save(update_fields=['amount_paid', 'updated_at'])
    return payment
