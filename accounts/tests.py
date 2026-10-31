from django.test import TestCase, override_settings
from django.core.management import call_command
from django.urls import reverse
from decimal import Decimal

from .models import User
from catalog.models import Plan, Product
from subscriptions.models import Subscription
from datetime import date


class AdminDashboardTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('admin@example.com', 'Strong-pass-123', name='Admin', role='admin')
        self.staff = User.objects.create_user('staff@example.com', 'Strong-pass-123', name='Staff', role='staff')
        self.customer = User.objects.create_user('customer@example.com', 'Strong-pass-123', name='Test Customer', role='customer')

    def test_admin_dashboard_is_admin_only(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse('admin_dashboard')).status_code, 403)
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse('admin_dashboard')).status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('admin_dashboard')).status_code, 200)

    def test_signup_duplicate_email_shows_a_form_error_not_a_server_error(self):
        User.objects.create_user('existing@example.com', 'Strong-pass-123', name='Existing', role='customer')
        response = self.client.post(reverse('signup'), {
            'name': 'New Person', 'email': 'EXISTING@example.com',
            'phone': '', 'company': '',
            'password1': 'Strong-pass-123', 'password2': 'Strong-pass-123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'An account with this email already exists.')
        self.assertEqual(User.objects.filter(email__iexact='existing@example.com').count(), 1)

    def test_dashboard_statistics_come_from_database(self):
        product = Product.objects.create(name='Live product', sales_price=Decimal('10.00'))
        plan = Plan.objects.create(name='Live plan', product=product, price=Decimal('12.00'))
        Subscription.objects.create(customer=self.customer, plan=plan, start_date=date(2026, 1, 1), status='active')
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.context['stats']['products_total'], 1)
        self.assertEqual(response.context['stats']['plans_active'], 1)
        self.assertEqual(response.context['stats']['subscriptions_active'], 1)

    def test_admin_login_redirects_to_dashboard_and_staff_to_home(self):
        response = self.client.post(reverse('login'), {'username': self.admin.email, 'password': 'Strong-pass-123'})
        self.assertRedirects(response, reverse('admin_dashboard'))
        self.client.logout()
        response = self.client.post(reverse('login'), {'username': self.staff.email, 'password': 'Strong-pass-123'})
        self.assertRedirects(response, reverse('home'))

    def test_product_owner_login_and_dashboard(self):
        owner = User.objects.create_user('owner@example.com', 'Strong-pass-123', name='Owner', role='product_owner')
        response = self.client.post(reverse('login'), {'username': owner.email, 'password': 'Strong-pass-123'})
        self.assertRedirects(response, reverse('product_owner_dashboard'))
        response = self.client.get(reverse('product_owner_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_create_product_owner_account(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('product_owner_list'), {
            'name': 'New Owner', 'email': 'new-owner@example.com', 'company': 'New Co',
            'password1': 'Valid-password-123', 'password2': 'Valid-password-123',
        })
        self.assertRedirects(response, reverse('product_owner_list'))
        owner = User.objects.get(email='new-owner@example.com')
        self.assertEqual(owner.role, 'product_owner')
        self.assertTrue(owner.check_password('Valid-password-123'))

    def test_customer_search_and_subscription_history(self):
        plan = Plan.objects.create(name='History plan', price=Decimal('5.00'))
        sub = Subscription.objects.create(customer=self.customer, plan=plan, start_date=date(2026, 1, 1))
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('customer_list'), {'q': 'Test Customer'}), 'Test Customer')
        self.assertContains(self.client.get(reverse('customer_detail', args=[self.customer.pk])), sub.subscription_number)

    def test_customer_dashboard_uses_live_subscription_counts(self):
        plan = Plan.objects.create(name='Customer plan', price=Decimal('5.00'))
        Subscription.objects.create(customer=self.customer, plan=plan, start_date=date(2026, 1, 1), status='active')
        self.client.force_login(self.customer)
        response = self.client.get(reverse('customer_portal'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['stats']['subscriptions_total'], 1)
        self.assertEqual(response.context['stats']['subscriptions_active'], 1)

    def test_customer_profile_updates_only_permitted_fields(self):
        self.client.force_login(self.customer)
        response = self.client.post(reverse('customer_profile'), {
            'name': 'Updated Name', 'email': self.customer.email,
            'phone': '1234567', 'company': 'Example Co', 'role': 'admin',
            'is_staff': 'on', 'is_superuser': 'on',
        })
        self.assertRedirects(response, reverse('customer_profile'))
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.name, 'Updated Name')
        self.assertEqual(self.customer.role, 'customer')
        self.assertFalse(self.customer.is_staff or self.customer.is_superuser)

    def test_customer_invoices_page_is_routed_and_role_protected(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse('customer_invoices'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No invoices yet')
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('customer_invoices')).status_code, 403)

    @override_settings(DEBUG=True)
    def test_local_admin_setup_command_is_idempotent_and_hashes_password(self):
        for _ in range(2):
            call_command('setup_local_admin', email='local-admin@example.com', password='Local-only-Password123')
        user = User.objects.get(email='local-admin@example.com')
        self.assertEqual(User.objects.filter(email='local-admin@example.com').count(), 1)
        self.assertEqual(user.role, 'admin')
        self.assertTrue(user.is_staff and user.is_superuser)
        self.assertTrue(user.check_password('Local-only-Password123'))
        self.assertNotEqual(user.password, 'Local-only-Password123')
