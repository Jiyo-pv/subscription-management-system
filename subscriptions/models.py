from django.conf import settings
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from catalog.models import Plan


class Subscription(models.Model):
    """Represents a customer subscription to a plan."""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('quotation', 'Quotation'),
        ('confirmed', 'Confirmed'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('closed', 'Closed'),
    ]

    PAYMENT_TERMS_CHOICES = [
        ('prepaid', 'Prepaid'),
        ('postpaid', 'Postpaid'),
        ('net_15', 'Net 15'),
        ('net_30', 'Net 30'),
        ('net_60', 'Net 60'),
    ]

    # Valid status transitions
    VALID_TRANSITIONS = {
        'draft': ['quotation', 'closed'],
        'quotation': ['confirmed', 'closed'],
        'confirmed': ['active', 'closed'],
        'active': ['paused', 'closed'],
        'paused': ['active', 'closed'],
        'closed': [],
    }

    subscription_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        limit_choices_to={'role': 'customer'}
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name='subscriptions'
    )
    start_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    payment_terms = models.CharField(
        max_length=20,
        choices=PAYMENT_TERMS_CHOICES,
        default='prepaid'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    next_billing_date = models.DateField(null=True, blank=True)
    template = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='derived_subscriptions'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_subscriptions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subscription_number} – {self.customer}"

    def save(self, *args, **kwargs):
        if not self.subscription_number:
            self.subscription_number = self._generate_subscription_number()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_subscription_number():
        """Generate next subscription number like SUB-0001."""
        last = Subscription.objects.order_by('-id').first()
        if last and last.subscription_number.startswith('SUB-'):
            try:
                last_num = int(last.subscription_number.split('-')[1])
            except (ValueError, IndexError):
                last_num = 0
        else:
            last_num = 0
        return f"SUB-{last_num + 1:04d}"

    def can_transition_to(self, new_status):
        """Check whether transition from current status to new_status is valid."""
        allowed = self.VALID_TRANSITIONS.get(self.status, [])
        return new_status in allowed

    def transition_to(self, new_status):
        """Transition the subscription to a new status with validation."""
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Cannot transition from '{self.get_status_display()}' "
                f"to '{dict(self.STATUS_CHOICES).get(new_status, new_status)}'."
            )
        self.status = new_status

        # When activating, set billing dates if not set
        if new_status == 'active':
            today = timezone.now().date()
            if not self.start_date or self.start_date > today:
                self.start_date = today
            if not self.next_billing_date:
                self.next_billing_date = self._calculate_next_billing_date(self.start_date)
            if not self.expiry_date and self.plan.end_date:
                self.expiry_date = self.plan.end_date

        self.save()

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.start_date and self.expiry_date and self.expiry_date <= self.start_date:
            raise ValidationError({'expiry_date': 'Expiry date must be after the start date.'})

    def _calculate_next_billing_date(self, from_date):
        """Calculate the next billing date based on the plan's billing period."""
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta

        period = self.plan.billing_period
        if period == 'daily':
            return from_date + timedelta(days=1)
        elif period == 'weekly':
            return from_date + timedelta(weeks=1)
        elif period == 'monthly':
            return from_date + relativedelta(months=1)
        elif period == 'yearly':
            return from_date + relativedelta(years=1)
        return from_date + relativedelta(months=1)

    @property
    def is_pausable(self):
        return self.status == 'active' and self.plan.is_pausable

    @property
    def is_closable(self):
        return self.status in ('draft', 'quotation', 'confirmed', 'active', 'paused') and self.plan.is_closable


class SubscriptionLine(models.Model):
    """Individual line item within a subscription."""

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='lines'
    )
    description = models.CharField(max_length=300)
    product = models.ForeignKey('catalog.Product', on_delete=models.PROTECT, null=True, blank=True)
    variant = models.ForeignKey('catalog.ProductVariant', on_delete=models.PROTECT, null=True, blank=True)
    tax = models.ForeignKey('catalog.Tax', on_delete=models.PROTECT, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.description} × {self.quantity}"

    @property
    def line_total(self):
        return self.amount or self.quantity * self.unit_price
