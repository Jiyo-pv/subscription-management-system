from django.db import models
from django.conf import settings
from django.utils import timezone
from simple_history.models import HistoricalRecords


class Product(models.Model):
    """Represents a product or service offered by the business."""

    TYPE_CHOICES = [
        ('service', 'Service'),
        ('software', 'Software'),
        ('addon', 'Add-on'),
    ]
    APPROVAL_PENDING = 'pending'
    APPROVAL_APPROVED = 'approved'
    APPROVAL_REJECTED = 'rejected'
    APPROVAL_CHANGES_REQUESTED = 'changes_requested'
    APPROVAL_STATUS_CHOICES = [
        (APPROVAL_PENDING, 'Pending'),
        (APPROVAL_APPROVED, 'Approved'),
        (APPROVAL_REJECTED, 'Rejected'),
        (APPROVAL_CHANGES_REQUESTED, 'Changes requested'),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        limit_choices_to={'role': 'product_owner'},
    )

    name = models.CharField(max_length=200)
    product_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='service',
        verbose_name='Type'
    )
    sales_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )
    description = models.TextField(blank=True, verbose_name='Notes / Description')
    is_active = models.BooleanField(default=True, verbose_name='Active')
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default=APPROVAL_PENDING,
        db_index=True,
    )
    approval_feedback = models.TextField(blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def is_customer_available(self):
        return self.is_active and self.approval_status == self.APPROVAL_APPROVED


class ProductVariant(models.Model):
    """Optional variant for a product with its own pricing."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants'
    )
    name = models.CharField(max_length=200)
    sales_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.product.name} – {self.name}"


class Plan(models.Model):
    """Subscription plan that customers can subscribe to."""

    BILLING_PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    name = models.CharField(max_length=200)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='plans',
        null=True,
        blank=True
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    billing_period = models.CharField(
        max_length=20,
        choices=BILLING_PERIOD_CHOICES,
        default='monthly'
    )
    min_quantity = models.PositiveIntegerField(default=1, verbose_name='Minimum quantity')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    auto_close = models.BooleanField(
        default=False,
        help_text='Automatically close subscription at end date'
    )
    is_closable = models.BooleanField(default=True, verbose_name='Closable')
    is_pausable = models.BooleanField(default=False, verbose_name='Pausable')
    is_renewable = models.BooleanField(default=True, verbose_name='Renewable')
    is_active = models.BooleanField(default=True, verbose_name='Active')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def is_available(self):
        """Check if the plan is currently available for subscription."""
        from django.utils import timezone
        today = timezone.now().date()

        if not self.is_active:
            return False
        if self.product_id and not self.product.is_customer_available:
            return False
        if self.start_date and today < self.start_date:
            return False
        if self.end_date and today > self.end_date:
            return False
        return True

    @property
    def billing_period_display(self):
        return dict(self.BILLING_PERIOD_CHOICES).get(self.billing_period, self.billing_period)
