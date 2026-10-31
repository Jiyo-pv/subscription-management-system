from django.conf import settings
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords


class Payment(models.Model):
    CASH = 'cash'
    CARD = 'card'
    BANK = 'bank_transfer'
    UPI = 'upi'
    CHEQUE = 'cheque'
    METHOD_CHOICES = [(CASH, 'Cash'), (CARD, 'Card'), (BANK, 'Bank transfer'), (UPI, 'UPI'), (CHEQUE, 'Cheque')]

    invoice = models.ForeignKey('billing.Invoice', on_delete=models.PROTECT, related_name='payments')
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField(default=timezone.localdate)
    note = models.TextField(blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='recorded_payments')
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    def __str__(self):
        return f'{self.invoice} – {self.amount}'
