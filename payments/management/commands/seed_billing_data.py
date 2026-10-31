from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from billing.models import Invoice
from catalog.models import Plan, Product
from subscriptions.models import Subscription

from payments.models import Payment


class Command(BaseCommand):
    help = 'Seed customers, active subscriptions, invoices, and payments for load testing.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=5000,
            help='Number of customer subscriptions to create (default: 5000).',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Bulk insert batch size (default: 500).',
        )

    def handle(self, *args, **options):
        count = options['count']
        batch_size = options['batch_size']
        if count < 1:
            raise ValueError('--count must be at least 1.')
        if batch_size < 1:
            raise ValueError('--batch-size must be at least 1.')

        with transaction.atomic():
            product, _ = Product.objects.get_or_create(
                name='Seed analytics product',
                defaults={
                    'sales_price': Decimal('99.00'),
                    'cost_price': Decimal('20.00'),
                    'approval_status': Product.APPROVAL_APPROVED,
                },
            )
            plan, _ = Plan.objects.get_or_create(
                name='Seed monthly plan',
                defaults={
                    'product': product,
                    'price': Decimal('99.00'),
                    'billing_period': 'monthly',
                    'is_active': True,
                },
            )

            user_start = User.objects.count() + 1
            subscription_start = Subscription.objects.count() + 1
            invoice_start = Invoice.objects.count() + 1
            today = timezone.localdate()
            password = make_password('SeedData-Only-123!')
            customers = [
                User(
                    email=f'seed-customer-{user_start + index}@example.test',
                    name=f'Seed Customer {user_start + index}',
                    company=f'Seed Company {user_start + index}',
                    role='customer',
                    password=password,
                    is_active=True,
                )
                for index in range(count)
            ]
            User.objects.bulk_create(customers, batch_size=batch_size)

            subscriptions = [
                Subscription(
                    subscription_number=f'SUB-{subscription_start + index:04d}',
                    customer=customer,
                    plan=plan,
                    start_date=today - timedelta(days=30),
                    next_billing_date=today + timedelta(days=30),
                    payment_terms='prepaid',
                    status='active',
                )
                for index, customer in enumerate(customers)
            ]
            Subscription.objects.bulk_create(subscriptions, batch_size=batch_size)

            invoices = []
            payments = []
            for index, subscription in enumerate(subscriptions):
                is_paid = index % 4 == 0
                is_overdue = index % 3 == 0 and not is_paid
                total = Decimal('99.00')
                amount_paid = total if is_paid else Decimal('49.50')
                due_date = today - timedelta(days=7) if is_overdue else today + timedelta(days=14)
                invoice = Invoice(
                    invoice_number=f'INV-{invoice_start + index:04d}',
                    subscription=subscription,
                    customer=subscription.customer,
                    issue_date=today - timedelta(days=30),
                    period_start=today - timedelta(days=30),
                    period_end=today,
                    due_date=due_date,
                    status=Invoice.PAID if is_paid else Invoice.OPEN,
                    paid_at=timezone.now() if is_paid else None,
                    subtotal=total,
                    total_amount=total,
                    amount_paid=amount_paid,
                )
                invoices.append(invoice)
            Invoice.objects.bulk_create(invoices, batch_size=batch_size)

            for invoice in invoices:
                payments.append(
                    Payment(
                        invoice=invoice,
                        method=Payment.UPI,
                        amount=invoice.amount_paid,
                        payment_date=today,
                        note='Seed payment',
                    )
                )
            Payment.objects.bulk_create(payments, batch_size=batch_size)

        self.stdout.write(
            self.style.SUCCESS(
                f'Created {count} customers, subscriptions, invoices, and payments.'
            )
        )
