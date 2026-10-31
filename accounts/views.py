from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Count, Q
import time
from .forms import SignupForm, StaffCreationForm, ProductOwnerCreationForm, CustomerProfileForm
from .decorators import role_required


def health(request):
    return JsonResponse({
        'status': 'ok'
    })


def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('login')

    else:
        form = SignupForm()

    return render(request, 'accounts/signup.html', {
        'form': form
    })

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 300  # 5 minutes


def login_view(request):
    now = time.time()

    failed_attempts = request.session.get('login_failed_attempts', 0)
    lockout_until = request.session.get('login_lockout_until')

    # Check whether the user is currently locked out
    if lockout_until and now < lockout_until:
        remaining = int(lockout_until - now)

        form = AuthenticationForm(request)

        form.add_error(
            None,
            f"Too many failed login attempts. "
            f"Please try again in {max(1, remaining // 60 + 1)} minute(s)."
        )

        return render(request, 'accounts/login.html', {
            'form': form
        })

    # Lockout period has expired
    if lockout_until and now >= lockout_until:
        request.session.pop('login_failed_attempts', None)
        request.session.pop('login_lockout_until', None)

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            # Successful login → reset failed attempts
            request.session.pop('login_failed_attempts', None)
            request.session.pop('login_lockout_until', None)

            user = form.get_user()
            login(request, user)

            if user.role == 'customer':
                return redirect('customer_portal')

            if user.role == 'admin':
                return redirect('admin_dashboard')

            if user.role == 'product_owner':
                return redirect('product_owner_dashboard')

            return redirect('home')

        else:
            # Failed login
            failed_attempts += 1
            request.session['login_failed_attempts'] = failed_attempts

            if failed_attempts >= MAX_LOGIN_ATTEMPTS:
                request.session['login_lockout_until'] = (
                    now + LOCKOUT_SECONDS
                )

                form.add_error(
                    None,
                    "Too many failed login attempts. "
                    "Please try again in 5 minutes."
                )

    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {
        'form': form
    })

def logout_view(request):
    logout(request)
    return redirect('login')


def home(request):
    if request.user.is_authenticated and request.user.role == 'admin':
        return redirect('admin_dashboard')
    if request.user.is_authenticated and request.user.role == 'product_owner':
        return redirect('product_owner_dashboard')
    if request.user.is_authenticated and request.user.role == 'customer':
        return redirect('customer_portal')
    return render(request, 'accounts/home.html')


@role_required('admin')
def admin_dashboard(request):
    from catalog.models import Plan, Product
    from subscriptions.models import Subscription

    subscription_counts = Subscription.objects.aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(status='active')),
        pending=Count('id', filter=Q(status__in=['draft', 'quotation', 'confirmed'])),
        closed=Count('id', filter=Q(status='closed')),
    )
    from accounts.models import User
    stats = {
        'product_owners_total': User.objects.filter(role='product_owner').count(),
        'customers_total': User.objects.filter(role='customer').count(),
        'products_total': Product.objects.count(),
        'products_active': Product.objects.filter(is_active=True).count(),
        'products_pending': Product.objects.filter(approval_status__in=[Product.APPROVAL_PENDING, Product.APPROVAL_CHANGES_REQUESTED]).count(),
        'products_approved': Product.objects.filter(approval_status=Product.APPROVAL_APPROVED).count(),
        'products_rejected': Product.objects.filter(approval_status=Product.APPROVAL_REJECTED).count(),
        'plans_total': Plan.objects.count(),
        'plans_active': Plan.objects.filter(is_active=True).count(),
        'subscriptions_total': subscription_counts['total'],
        'subscriptions_active': subscription_counts['active'],
        'subscriptions_pending': subscription_counts['pending'],
        'subscriptions_closed': subscription_counts['closed'],
    }
    recent_subscriptions = Subscription.objects.select_related(
        'customer', 'plan'
    ).order_by('-created_at')[:8]
    pending_products = Product.objects.select_related('owner').filter(
        approval_status__in=[Product.APPROVAL_PENDING, Product.APPROVAL_CHANGES_REQUESTED]
    ).order_by('-submitted_at')[:10]
    recent_products = Product.objects.select_related('owner').order_by('-submitted_at')[:8]
    recent_product_owners = User.objects.filter(role='product_owner').order_by('-date_joined')[:6]
    activity = []
    for product in recent_products:
        activity.append({'when': product.submitted_at, 'label': f'Product submitted: {product.name}', 'detail': product.owner.name if product.owner else 'Legacy listing', 'url': f'/products/{product.pk}/'})
    for owner in recent_product_owners:
        activity.append({'when': owner.date_joined, 'label': f'Product Owner registered: {owner.name}', 'detail': owner.email, 'url': '/admin-dashboard/product-owners/'})
    for subscription in recent_subscriptions:
        activity.append({'when': subscription.created_at, 'label': f'Subscription created: {subscription.subscription_number}', 'detail': subscription.customer.name, 'url': f'/subscriptions/{subscription.pk}/'})
    activity.sort(key=lambda item: item['when'], reverse=True)
    cards = [
        ('Product owners', stats['product_owners_total'], '♙', '/admin-dashboard/product-owners/'),
        ('Customers', stats['customers_total'], '♙', '/admin-dashboard/customers/'),
        ('Total products', stats['products_total'], '▣', '/products/'),
        ('Pending approvals', stats['products_pending'], '◷', '/products/?approval=pending'),
        ('Approved products', stats['products_approved'], '✓', '/products/?approval=approved'),
        ('Rejected products', stats['products_rejected'], '!', '/products/?approval=rejected'),
        ('Total plans', stats['plans_total'], '◈', '/plans/'),
        ('Subscriptions', stats['subscriptions_total'], '◇', '/subscriptions/'),
        ('Active subscriptions', stats['subscriptions_active'], '↻', '/subscriptions/?status=active'),
    ]
    return render(request, 'accounts/admin_dashboard.html', {
        'stats': stats,
        'cards': cards,
        'recent_subscriptions': recent_subscriptions,
        'pending_products': pending_products,
        'recent_products': recent_products,
        'recent_product_owners': recent_product_owners,
        'platform_activity': activity[:12],
        'active': 'dashboard',
    })


@role_required('admin')
def product_owner_list(request):
    from accounts.models import User
    if request.method == 'POST':
        form = ProductOwnerCreationForm(request.POST)
        if form.is_valid():
            owner = form.save()
            messages.success(request, f'Product Owner {owner.email} created.')
            return redirect('product_owner_list')
    else:
        form = ProductOwnerCreationForm()
    owners = User.objects.filter(role='product_owner').annotate(
        product_count=Count('products')
    ).order_by('-date_joined')
    return render(request, 'accounts/product_owner_list.html', {
        'owners': owners,
        'form': form,
        'active': 'owners',
    })


@role_required('product_owner')
def product_owner_profile(request):
    return render(request, 'accounts/product_owner_profile.html')


@role_required('admin')
def toggle_product_owner_active(request, pk):
    from accounts.models import User
    owner = get_object_or_404(User, pk=pk, role='product_owner')
    if request.method == 'POST':
        owner.is_active = not owner.is_active
        owner.save(update_fields=['is_active'])
        messages.success(request, f'Product Owner account {"enabled" if owner.is_active else "disabled"}.')
    return redirect('product_owner_list')


@role_required('admin')
def customer_list(request):
    from accounts.models import User
    customers = User.objects.filter(role='customer').annotate(
        subscription_count=Count('subscriptions')
    ).order_by('name', 'email')
    search = request.GET.get('q', '').strip()
    if search:
        customers = customers.filter(Q(name__icontains=search) | Q(email__icontains=search))
    page_obj = Paginator(customers, 20).get_page(request.GET.get('page'))
    return render(request, 'accounts/customer_list.html', {
        'customers': page_obj.object_list,
        'page_obj': page_obj,
        'search': search,
        'active': 'customers',
    })


@role_required('admin')
def customer_detail(request, pk):
    from accounts.models import User
    from subscriptions.models import Subscription
    customer = get_object_or_404(User, pk=pk, role='customer')
    subscriptions = Subscription.objects.filter(customer=customer).select_related(
        'plan', 'plan__product'
    ).order_by('-created_at')
    page_obj = Paginator(subscriptions, 15).get_page(request.GET.get('page'))
    return render(request, 'accounts/customer_detail.html', {
        'customer': customer,
        'subscriptions': page_obj.object_list,
        'page_obj': page_obj,
        'active': 'customers',
    })


@role_required('admin')
def admin_test(request):
    return HttpResponse("You are an ADMIN!")


@role_required('admin')
def create_staff(request):
    if request.method == 'POST':
        form = StaffCreationForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('home')

    else:
        form = StaffCreationForm()

    return render(
        request,
        'accounts/create_staff.html',
        {'form': form}
    )


@role_required('customer')
def customer_portal(request):
    from subscriptions.models import Subscription
    from subscriptions.services import get_public_products
    subscriptions = Subscription.objects.filter(
        customer=request.user
    ).select_related('plan', 'plan__product').order_by('-created_at')
    stats = {
        'subscriptions_total': subscriptions.count(),
        'subscriptions_active': subscriptions.filter(status='active').count(),
        'subscriptions_pending': subscriptions.filter(status__in=['draft', 'quotation', 'confirmed']).count(),
        'subscriptions_closed': subscriptions.filter(status='closed').count(),
    }
    products = get_public_products()
    return render(
        request,
        'accounts/customer_portal.html',
        {
            'subscriptions': subscriptions[:5],
            'recent_activity': subscriptions[:5],
            'products': products[:4],
            'available_products_count': len(products),
            'stats': stats,
            'active': 'dashboard',
        }
    )


@role_required('customer')
def customer_profile(request):
    if request.method == 'POST':
        form = CustomerProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile was updated.')
            return redirect('customer_profile')
    else:
        form = CustomerProfileForm(instance=request.user)
    return render(request, 'accounts/customer_profile.html', {
        'form': form,
        'active': 'profile',
    })


@role_required('customer')
def customer_invoices(request):
    from billing.models import Invoice
    invoices = Invoice.objects.filter(customer=request.user).select_related(
        'subscription', 'subscription__plan', 'subscription__plan__product'
    )
    return render(request, 'billing/customer_invoice_list.html', {
        'invoices': invoices,
        'active': 'invoices',
    })
