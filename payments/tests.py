from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User
from billing.services import generate_invoice
from catalog.models import Plan, Product
from subscriptions.models import Subscription

from .services import record_payment


class PaymentServiceTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user('customer@example.com', 'Strong-pass-123', name='Customer', role='customer')
        self.staff = User.objects.create_user('staff@example.com', 'Strong-pass-123', name='Staff', role='staff')
        owner = User.objects.create_user('owner@example.com', 'Strong-pass-123', name='Owner', role='product_owner')
        self.subscription = Subscription.objects.create(customer=self.customer, plan=Plan.objects.create(name='Monthly', product=Product.objects.create(name='Product', owner=owner), price=Decimal('10.00')), start_date=date.today(), status='active')
        self.invoice = generate_invoice(self.subscription)

    def test_partial_then_final_payment_marks_invoice_paid(self):
        record_payment(self.invoice, 'upi', Decimal('4.00'), date.today(), recorded_by=self.staff)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.amount_paid, Decimal('4.00'))
        record_payment(self.invoice, 'upi', Decimal('6.00'), date.today(), recorded_by=self.staff)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'paid')

    def test_overpayment_is_rejected(self):
        with self.assertRaises(ValidationError):
            record_payment(self.invoice, 'cash', Decimal('10.01'), date.today(), recorded_by=self.staff)
