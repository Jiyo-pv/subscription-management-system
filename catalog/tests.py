from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from .models import Plan, Product


class CatalogAccessTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('admin@example.com', 'Strong-pass-123', name='Admin', role='admin')
        self.staff = User.objects.create_user('staff@example.com', 'Strong-pass-123', name='Staff', role='staff')
        self.owner = User.objects.create_user('owner@example.com', 'Strong-pass-123', name='Owner', role='product_owner')
        self.other_owner = User.objects.create_user('other@example.com', 'Strong-pass-123', name='Other Owner', role='product_owner')
        self.customer = User.objects.create_user('customer@example.com', 'Strong-pass-123', name='Customer', role='customer')
        self.product = Product.objects.create(
            name='Cloud', owner=self.owner, sales_price=Decimal('15.00'),
            approval_status=Product.APPROVAL_APPROVED,
        )
        self.plan = Plan.objects.create(name='Monthly', product=self.product, price=Decimal('15.00'))

    def test_product_owner_creates_pending_product_ignoring_submitted_owner(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('product_create'), {
            'name': 'New service', 'product_type': 'service', 'sales_price': '20.00',
            'cost_price': '5.00', 'description': 'Test', 'owner': self.other_owner.pk,
        })
        product = Product.objects.get(name='New service')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(product.owner, self.owner)
        self.assertEqual(product.approval_status, Product.APPROVAL_PENDING)

    def test_product_owner_cannot_access_another_owners_products_or_plans(self):
        other_product = Product.objects.create(name='Private', owner=self.other_owner)
        other_plan = Plan.objects.create(name='Private plan', product=other_product, price=Decimal('5.00'))
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse('product_edit', args=[other_product.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('product_detail', args=[other_product.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('plan_edit', args=[other_plan.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('plan_detail', args=[other_plan.pk])).status_code, 404)

    def test_admin_reviews_and_owner_can_resubmit(self):
        pending = Product.objects.create(name='Review me', owner=self.owner)
        self.client.force_login(self.admin)
        response = self.client.post(reverse('product_review', args=[pending.pk, 'request-changes']), {'feedback': 'Add a clearer description.'})
        pending.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(pending.approval_status, Product.APPROVAL_CHANGES_REQUESTED)
        self.assertEqual(pending.approval_feedback, 'Add a clearer description.')
        self.client.force_login(self.owner)
        response = self.client.post(reverse('product_edit', args=[pending.pk]), {
            'name': 'Review me updated', 'product_type': 'service', 'sales_price': '0.00',
            'cost_price': '0.00', 'description': 'Clear updated information.',
        })
        pending.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(pending.approval_status, Product.APPROVAL_PENDING)
        self.assertEqual(pending.approval_feedback, '')
        self.client.force_login(self.admin)
        self.client.post(reverse('product_review', args=[pending.pk, 'approve']), {})
        pending.refresh_from_db()
        self.assertEqual(pending.approval_status, Product.APPROVAL_APPROVED)
        self.assertIsNotNone(pending.approved_at)

    def test_admin_cannot_create_products_or_plans(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('product_create')).status_code, 403)
        self.assertEqual(self.client.get(reverse('plan_create')).status_code, 403)

    def test_owner_cannot_create_plan_for_another_owner_product(self):
        other_product = Product.objects.create(
            name='Other', owner=self.other_owner, approval_status=Product.APPROVAL_APPROVED,
        )
        self.client.force_login(self.owner)
        response = self.client.post(reverse('plan_create'), {
            'name': 'Forbidden plan', 'product': other_product.pk, 'price': '1.00',
            'billing_period': 'monthly', 'min_quantity': '1', 'is_active': 'on',
            'is_closable': 'on', 'is_renewable': 'on',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Plan.objects.filter(name='Forbidden plan').exists())

    def test_customer_sees_only_approved_active_product_plans(self):
        pending = Product.objects.create(name='Pending', owner=self.owner)
        Plan.objects.create(name='Pending plan', product=pending, price=Decimal('2.00'))
        approved_without_plan = Product.objects.create(
            name='Approved without plan', owner=self.other_owner,
            approval_status=Product.APPROVAL_APPROVED,
        )
        inactive = Product.objects.create(name='Inactive', owner=self.owner, is_active=False, approval_status=Product.APPROVAL_APPROVED)
        Plan.objects.create(name='Inactive plan', product=inactive, price=Decimal('3.00'))
        self.client.force_login(self.customer)
        response = self.client.get(reverse('pricing_page'))
        self.assertContains(response, 'Cloud')
        self.assertContains(response, 'Monthly')
        self.assertContains(response, approved_without_plan.name)
        self.assertContains(response, 'Pricing plans are not available yet')
        self.assertNotContains(response, 'Pending')
        self.assertNotContains(response, 'Inactive')

    def test_owner_product_list_contains_only_the_signed_in_owners_records(self):
        Product.objects.create(name='Other private listing', owner=self.other_owner)
        self.client.force_login(self.owner)
        response = self.client.get(reverse('product_list'))
        self.assertContains(response, self.product.name)
        self.assertNotContains(response, 'Other private listing')

    def test_customer_cannot_subscribe_to_pending_product_plan(self):
        pending = Product.objects.create(name='Pending', owner=self.owner)
        plan = Plan.objects.create(name='Pending plan', product=pending, price=Decimal('2.00'))
        self.client.force_login(self.customer)
        response = self.client.post(reverse('subscribe_to_plan', args=[plan.pk]))
        self.assertRedirects(response, reverse('pricing_page'))
        self.assertFalse(self.customer.subscriptions.exists())
