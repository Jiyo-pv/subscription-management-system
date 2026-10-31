from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords


class Invoice(models.Model):
    DRAFT = 'draft'
    OPEN = 'open'
    PAID = 'paid'
    VOID = 'void'
    STATUS_CHOICES = [
        (DRAFT, 'Draft'),
        (OPEN, 'Open'),
        (PAID, 'Paid'),
        (VOID, 'Void'),
    ]

    invoice_number = models.CharField(max_length=20, unique=True, editable=False)
    subscription = models.ForeignKey('subscriptions.Subscription', on_delete=models.PROTECT, related_name='invoices')
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='invoices')
    issue_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=DRAFT)
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['-issue_date', '-id']

    def __str__(self):
        return self.invoice_number

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            last = Invoice.objects.order_by('-id').first()
            last_number = int(last.invoice_number.split('-')[1]) if last else 0
            self.invoice_number = f'INV-{last_number + 1:04d}'
        if self.subscription_id:
            self.customer_id = self.subscription.customer_id
        super().save(*args, **kwargs)

    @property
    def total(self):
        return sum((line.line_total for line in self.lines.all()), Decimal('0.00'))

    @property
    def is_overdue(self):
        return self.status == self.OPEN and self.due_date < timezone.localdate()

    def mark_paid(self):
        if self.status != self.OPEN:
            raise ValueError('Only open invoices can be marked paid.')
        self.status = self.PAID
        self.paid_at = timezone.now()
        self.save(update_fields=['status', 'paid_at', 'updated_at'])


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='lines')
    description = models.CharField(max_length=300)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.description

    @property
    def line_total(self):
        return self.quantity * self.unit_price
