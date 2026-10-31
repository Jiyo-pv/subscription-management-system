from decimal import Decimal

from django.db.models import F, Q
from django.utils import timezone

from .models import Discount


def calculate_totals(lines, discounts=()):
    """Calculate discount-before-tax totals with Decimal arithmetic only."""
    normalized = list(lines)
    subtotal = sum((line['quantity'] * line['unit_price'] for line in normalized), Decimal('0.00'))
    quantity = sum((line['quantity'] for line in normalized), 0)
    discount_total = Decimal('0.00')
    for discount in discounts:
        if subtotal < discount.min_purchase or quantity < discount.min_quantity:
            continue
        amount = subtotal * discount.value / Decimal('100') if discount.discount_type == Discount.PERCENT else discount.value
        discount_total += min(amount, subtotal - discount_total)
    taxable_subtotal = subtotal - discount_total
    tax_total = sum((
        (line['quantity'] * line['unit_price']) * (taxable_subtotal / subtotal if subtotal else Decimal('0.00')) * line.get('tax_percent', Decimal('0.00')) / Decimal('100')
        for line in normalized
    ), Decimal('0.00'))
    return {'subtotal': subtotal, 'discount_total': discount_total, 'tax_total': tax_total, 'total': taxable_subtotal + tax_total}


def get_applicable_discounts(subscription, today=None):
    today = today or timezone.localdate()
    product = subscription.plan.product
    discounts = Discount.objects.filter(is_active=True).filter(
        Q(start_date__isnull=True) | Q(start_date__lte=today),
        Q(end_date__isnull=True) | Q(end_date__gte=today),
        apply_to__in=[Discount.SUBSCRIPTION, Discount.PRODUCT],
    ).distinct()
    return [discount for discount in discounts if (
        discount.apply_to == Discount.SUBSCRIPTION or not discount.products.exists() or discount.products.filter(pk=product.pk).exists()
    ) and (discount.usage_limit is None or discount.times_used < discount.usage_limit)]


def consume_discount(discount):
    """Atomically consume one available use; returns False when exhausted."""
    filters = {'pk': discount.pk}
    if discount.usage_limit is not None:
        filters['times_used__lt'] = discount.usage_limit
    updated = Discount.objects.filter(**filters).update(times_used=F('times_used') + 1)
    return bool(updated)
