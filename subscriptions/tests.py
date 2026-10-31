from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from catalog.models import Plan
from catalog.models import Product
from .models import Subscription


class SubscriptionSecurityAndLifecycleTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user('one@example.com', 'Strong-pass-123', name='One', role='customer')
        self.other_customer = User.objects.create_user('two@example.com', 'Strong-pass-123', name='Two', role='customer')
        self.staff = User.objects.create_user('staff@example.com', 'Strong-pass-123', name='Staff', role='staff')
        self.plan = Plan.objects.create(name='Monthly', price=Decimal('9.99'))
        self.subscription = Subscription.objects.create(customer=self.customer, plan=self.plan, start_date=date(2026, 1, 1))

    def test_customer_cannot_access_another_customers_subscription(self):
        self.client.force_login(self.other_customer)
        response = self.client.get(reverse('my_subscription_detail', args=[self.subscription.pk]))
        self.assertEqual(response.status_code, 404)

    def test_customer_portal_shows_own_subscription(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse('customer_portal'))
        self.assertContains(response, self.subscription.subscription_number)

    def test_lifecycle_requires_quotation_before_confirmation(self):
        with self.assertRaises(ValueError):
            self.subscription.transition_to('confirmed')
        self.subscription.transition_to('quotation')
        self.subscription.transition_to('confirmed')
        self.subscription.transition_to('active')
        self.assertEqual(self.subscription.status, 'active')

    def test_subscription_numbers_are_generated(self):
        self.assertRegex(self.subscription.subscription_number, r'^SUB-\d{4,}$')

    def test_customer_can_subscribe_to_plan_for_approved_product(self):
        owner = User.objects.create_user('owner@example.com', 'Strong-pass-123', name='Owner', role='product_owner')
        product = Product.objects.create(name='Published', owner=owner, approval_status=Product.APPROVAL_APPROVED)
        plan = Plan.objects.create(name='Published monthly', product=product, price=Decimal('19.00'))
        self.client.force_login(self.other_customer)
        response = self.client.post(reverse('subscribe_to_plan', args=[plan.pk]))
        created = Subscription.objects.get(customer=self.other_customer, plan=plan)
        self.assertRedirects(response, reverse('my_subscription_detail', args=[created.pk]))
        self.assertEqual(created.status, 'quotation')

    def test_customer_cannot_subscribe_to_plan_for_pending_product(self):
        owner = User.objects.create_user('owner@example.com', 'Strong-pass-123', name='Owner', role='product_owner')
        product = Product.objects.create(name='Pending', owner=owner)
        plan = Plan.objects.create(name='Pending monthly', product=product, price=Decimal('19.00'))
        self.client.force_login(self.other_customer)
        response = self.client.post(reverse('subscribe_to_plan', args=[plan.pk]))
        self.assertRedirects(response, reverse('pricing_page'))
        self.assertFalse(Subscription.objects.filter(customer=self.other_customer, plan=plan).exists())

    def test_customer_browse_and_product_detail_pages_work_for_approved_products(self):
        owner = User.objects.create_user('owner@example.com', 'Strong-pass-123', name='Owner', role='product_owner', company='Provider Co')
        product = Product.objects.create(name='Published product', owner=owner, approval_status=Product.APPROVAL_APPROVED)
        Plan.objects.create(name='Published plan', product=product, price=Decimal('19.00'))
        pending = Product.objects.create(name='Not published', owner=owner)
        self.client.force_login(self.customer)
        browse = self.client.get(reverse('customer_products'))
        self.assertContains(browse, 'Published product')
        self.assertContains(browse, 'Provider Co')
        self.assertNotContains(browse, 'Not published')
        detail = self.client.get(reverse('customer_product_detail', args=[product.pk]))
        self.assertContains(detail, 'Published plan')
        self.assertEqual(self.client.get(reverse('customer_product_detail', args=[pending.pk])).status_code, 404)

    def test_customer_navigation_pages_all_resolve(self):
        self.client.force_login(self.customer)
        for route_name in ('customer_portal', 'customer_products', 'pricing_page', 'my_subscriptions', 'customer_invoices', 'customer_profile'):
            with self.subTest(route=route_name):
                self.assertEqual(self.client.get(reverse(route_name)).status_code, 200)

    def test_customer_cannot_open_product_owner_or_admin_pages(self):
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse('admin_dashboard')).status_code, 403)
        self.assertEqual(self.client.get(reverse('product_owner_dashboard')).status_code, 403)
        self.assertEqual(self.client.get(reverse('product_create')).status_code, 403)

    def test_customer_can_cancel_a_quotation_using_lifecycle(self):
        self.client.force_login(self.customer)
        response = self.client.post(reverse('customer_cancel_subscription', args=[self.subscription.pk]))
        self.assertRedirects(response, reverse('my_subscription_detail', args=[self.subscription.pk]))
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, 'closed')

    def test_customer_can_pause_and_resume_when_plan_allows_it(self):
        self.plan.is_pausable = True
        self.plan.save()
        self.subscription.status = 'active'
        self.subscription.save()
        self.client.force_login(self.customer)
        self.client.post(reverse('customer_pause_subscription', args=[self.subscription.pk]))
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, 'paused')
        self.client.post(reverse('customer_resume_subscription', args=[self.subscription.pk]))
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, 'active')

    def test_duplicate_open_plan_subscription_is_redirected_without_creating_another(self):
        owner = User.objects.create_user('owner@example.com', 'Strong-pass-123', name='Owner', role='product_owner')
        product = Product.objects.create(name='Published', owner=owner, approval_status=Product.APPROVAL_APPROVED)
        plan = Plan.objects.create(name='Published monthly', product=product, price=Decimal('19.00'))
        self.client.force_login(self.other_customer)
        first = self.client.post(reverse('subscribe_to_plan', args=[plan.pk]))
        created = Subscription.objects.get(customer=self.other_customer, plan=plan)
        self.assertEqual(first.status_code, 302)
        second = self.client.post(reverse('subscribe_to_plan', args=[plan.pk]))
        self.assertRedirects(second, reverse('my_subscription_detail', args=[created.pk]))
        self.assertEqual(Subscription.objects.filter(customer=self.other_customer, plan=plan).count(), 1)

    def test_customer_can_change_plan_to_another_published_plan(self):
        owner = User.objects.create_user('owner@example.com', 'Strong-pass-123', name='Owner', role='product_owner')
        product = Product.objects.create(name='Published', owner=owner, approval_status=Product.APPROVAL_APPROVED)
        current_plan = Plan.objects.create(name='Current', product=product, price=Decimal('10.00'))
        new_plan = Plan.objects.create(name='New', product=product, price=Decimal('20.00'))
        active_subscription = Subscription.objects.create(
            customer=self.customer, plan=current_plan, start_date=date(2026, 1, 1), status='active'
        )
        self.client.force_login(self.customer)
        response = self.client.post(reverse('customer_change_plan', args=[active_subscription.pk]), {'new_plan_id': new_plan.pk})
        self.assertRedirects(response, reverse('my_subscription_detail', args=[active_subscription.pk]))
        active_subscription.refresh_from_db()
        self.assertEqual(active_subscription.plan, new_plan)
