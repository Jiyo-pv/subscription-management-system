from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from catalog.models import Discount, Plan, Product, Tax
from subscriptions.models import Subscription, SubscriptionLine

from .models import Invoice
from .services import create_invoice_for_subscription


class InvoiceFlowTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user('customer@example.com', 'Strong-pass-123', name='Customer', role='customer')
        self.other_customer = User.objects.create_user('other@example.com', 'Strong-pass-123', name='Other', role='customer')
        self.staff = User.objects.create_user('staff@example.com', 'Strong-pass-123', name='Staff', role='staff')
        self.owner = User.objects.create_user('owner@example.com', 'Strong-pass-123', name='Owner', role='product_owner')
        product = Product.objects.create(name='Billing product', owner=self.owner)
        self.plan = Plan.objects.create(name='Monthly', product=product, price=Decimal('25.00'), min_quantity=2)
        self.subscription = Subscription.objects.create(
            customer=self.customer, plan=self.plan, start_date=date.today(), status='active'
        )

    def test_invoice_uses_plan_price_and_quantity(self):
        invoice = create_invoice_for_subscription(self.subscription, due_date=date.today() + timedelta(days=7))
        self.assertEqual(invoice.status, Invoice.OPEN)
        self.assertEqual(invoice.customer, self.customer)
        self.assertEqual(invoice.total, Decimal('50.00'))
        self.assertRegex(invoice.invoice_number, r'^INV-\d{4,}$')

    def test_customer_can_only_view_own_invoice(self):
        invoice = create_invoice_for_subscription(self.subscription)
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse('invoice_detail', args=[invoice.pk])).status_code, 200)
        self.client.force_login(self.other_customer)
        self.assertEqual(self.client.get(reverse('invoice_detail', args=[invoice.pk])).status_code, 404)

    def test_staff_can_create_an_invoice(self):
        self.client.force_login(self.staff)
        due_date = timezone.localdate() + timedelta(days=10)
        response = self.client.post(reverse('invoice_create', args=[self.subscription.pk]), {'due_date': due_date, 'notes': 'Thank you.'})
        invoice = Invoice.objects.get(subscription=self.subscription)
        self.assertRedirects(response, reverse('invoice_detail', args=[invoice.pk]))
        self.assertEqual(invoice.notes, 'Thank you.')
        self.assertEqual(invoice.status, Invoice.OPEN)

    def test_activation_creates_the_first_invoice(self):
        self.subscription.status = 'confirmed'
        self.subscription.save()
        self.client.force_login(self.staff)
        response = self.client.post(reverse('subscription_activate', args=[self.subscription.pk]))
        self.assertRedirects(response, reverse('subscription_detail', args=[self.subscription.pk]))
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, 'active')
        self.assertTrue(Invoice.objects.filter(subscription=self.subscription, status=Invoice.OPEN).exists())

    def test_invoice_cannot_be_created_for_a_draft_subscription(self):
        self.subscription.status = 'draft'
        self.subscription.save()
        self.client.force_login(self.staff)
        response = self.client.get(reverse('invoice_create', args=[self.subscription.pk]))
        self.assertRedirects(response, reverse('subscription_detail', args=[self.subscription.pk]))
        self.assertFalse(Invoice.objects.exists())

    def test_same_period_is_billed_only_once(self):
        first = create_invoice_for_subscription(self.subscription)
        second = create_invoice_for_subscription(self.subscription)
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertEqual(Invoice.objects.filter(subscription=self.subscription).count(), 1)

    def test_invoice_applies_tax_and_discount_once(self):
        tax = Tax.objects.create(name='GST', percent=Decimal('10.00'))
        SubscriptionLine.objects.create(subscription=self.subscription, description='Service', product=self.plan.product, tax=tax, quantity=1, unit_price=Decimal('100.00'))
        discount = Discount.objects.create(name='Launch', discount_type='percent', value=Decimal('10.00'))
        invoice = create_invoice_for_subscription(self.subscription)
        self.assertEqual(invoice.subtotal, Decimal('100.00'))
        self.assertEqual(invoice.discount_total, Decimal('10.00'))
        self.assertEqual(invoice.tax_total, Decimal('9.00'))
        self.assertEqual(invoice.total, Decimal('99.00'))
        discount.refresh_from_db()
        self.assertEqual(discount.times_used, 1)

    def test_run_billing_is_idempotent_and_advances_date(self):
        self.subscription.next_billing_date = date.today()
        self.subscription.save()
        call_command('run_billing')
        self.assertEqual(Invoice.objects.filter(subscription=self.subscription).count(), 1)
        self.subscription.refresh_from_db()
        first_next_date = self.subscription.next_billing_date
        call_command('run_billing')
        self.assertEqual(Invoice.objects.filter(subscription=self.subscription).count(), 1)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.next_billing_date, first_next_date)
