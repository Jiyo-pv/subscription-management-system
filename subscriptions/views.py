from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone

from accounts.decorators import role_required
from catalog.models import Plan, Product
from .models import Subscription
from .forms import SubscriptionCreateForm, SubscriptionEditForm
from .services import get_public_products


# ─── Staff / Admin subscription management ──────────────────


@role_required('admin', 'staff', 'product_owner')
def subscription_list(request):
    """List all subscriptions with search and filtering."""
    subscriptions = Subscription.objects.select_related(
        'customer', 'plan', 'plan__product'
    ).all()
    if request.user.role == 'product_owner':
        subscriptions = subscriptions.filter(plan__product__owner=request.user)

    search = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    plan_id = request.GET.get('plan', '')
    start_after = request.GET.get('start_after', '')
    start_before = request.GET.get('start_before', '')

    if search:
        subscriptions = subscriptions.filter(
            Q(subscription_number__icontains=search) |
            Q(customer__name__icontains=search) |
            Q(customer__email__icontains=search)
        )
    if status:
        subscriptions = subscriptions.filter(status=status)
    if plan_id:
        subscriptions = subscriptions.filter(plan_id=plan_id)
    if start_after:
        subscriptions = subscriptions.filter(start_date__gte=start_after)
    if start_before:
        subscriptions = subscriptions.filter(start_date__lte=start_before)

    plans = Plan.objects.filter(is_active=True)
    if request.user.role == 'product_owner':
        plans = plans.filter(product__owner=request.user)

    page_obj = Paginator(subscriptions, 25).get_page(request.GET.get('page'))
    return render(request, 'subscriptions/subscription_list.html', {
        'subscriptions': page_obj.object_list,
        'page_obj': page_obj,
        'search': search,
        'current_status': status,
        'current_plan': plan_id,
        'start_after': start_after,
        'start_before': start_before,
        'status_choices': Subscription.STATUS_CHOICES,
        'plans': plans,
    })


@role_required('admin', 'staff')
def subscription_create(request):
    """Create a new subscription."""
    if request.method == 'POST':
        form = SubscriptionCreateForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                subscription = form.save(commit=False)
                subscription.created_by = request.user
                subscription.save()
            messages.success(
                request,
                f'Subscription {subscription.subscription_number} created.'
            )
            return redirect('subscription_detail', pk=subscription.pk)
    else:
        form = SubscriptionCreateForm()

    return render(request, 'subscriptions/subscription_form.html', {
        'form': form,
        'title': 'Create subscription',
        'submit_label': 'Create subscription',
    })


@role_required('admin', 'staff', 'product_owner')
def subscription_detail(request, pk):
    """View subscription details."""
    subscriptions = Subscription.objects.select_related(
            'customer', 'plan', 'plan__product', 'created_by'
        )
    if request.user.role == 'product_owner':
        subscriptions = subscriptions.filter(plan__product__owner=request.user)
    subscription = get_object_or_404(subscriptions, pk=pk)

    return render(request, 'subscriptions/subscription_detail.html', {
        'subscription': subscription,
    })


@role_required('admin', 'staff')
def subscription_edit(request, pk):
    """Edit an existing subscription."""
    subscription = get_object_or_404(Subscription, pk=pk)

    if subscription.status == 'closed':
        messages.error(request, 'Cannot edit a closed subscription.')
        return redirect('subscription_detail', pk=pk)

    if request.method == 'POST':
        form = SubscriptionEditForm(request.POST, instance=subscription)
        if form.is_valid():
            form.save()
            messages.success(request, 'Subscription updated successfully.')
            return redirect('subscription_detail', pk=pk)
    else:
        form = SubscriptionEditForm(instance=subscription)

    return render(request, 'subscriptions/subscription_form.html', {
        'form': form,
        'subscription': subscription,
        'title': f'Edit {subscription.subscription_number}',
        'submit_label': 'Save changes',
    })


@role_required('admin', 'staff')
def subscription_confirm(request, pk):
    """Confirm a subscription (draft/quotation → confirmed)."""
    subscription = get_object_or_404(Subscription, pk=pk)

    if request.method == 'POST':
        try:
            if subscription.status == 'draft':
                subscription.transition_to('quotation')
                messages.success(request, 'Quotation created.')
            else:
                subscription.transition_to('confirmed')
                messages.success(request, 'Subscription confirmed.')
        except ValueError as e:
            messages.error(request, str(e))

    return redirect('subscription_detail', pk=pk)


@role_required('admin', 'staff')
def subscription_activate(request, pk):
    """Activate a confirmed subscription."""
    subscription = get_object_or_404(Subscription, pk=pk)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                subscription.transition_to('active')
            messages.success(request, 'Subscription activated.')
        except ValueError as e:
            messages.error(request, str(e))

    return redirect('subscription_detail', pk=pk)


@role_required('admin', 'staff')
def subscription_close(request, pk):
    """Close a subscription."""
    subscription = get_object_or_404(Subscription, pk=pk)

    if request.method == 'POST':
        try:
            subscription.transition_to('closed')
            messages.success(request, 'Subscription closed.')
        except ValueError as e:
            messages.error(request, str(e))

    return redirect('subscription_detail', pk=pk)


# ─── Customer self-service ───────────────────────────────────


@role_required('customer')
def pricing_page(request):
    products = get_public_products()
    return render(request, 'subscriptions/pricing.html', {
        'products': products,
        'active': 'products' if request.path == '/browse-products/' else 'pricing',
    })


@role_required('customer')
def subscribe_to_plan(request, plan_id):
    """Customer subscribes to a specific plan."""
    plan = get_object_or_404(Plan, pk=plan_id)

    if not plan.product_id or not plan.is_available or not plan.product.is_customer_available:
        messages.error(request, 'This plan is not currently available.')
        return redirect('pricing_page')

    existing = Subscription.objects.filter(
        customer=request.user,
        plan=plan,
        status__in=['draft', 'quotation', 'confirmed', 'active', 'paused'],
    ).first()
    if existing:
        messages.info(request, 'You already have an open subscription for this plan.')
        return redirect('my_subscription_detail', pk=existing.pk)

    if request.method == 'POST':
        with transaction.atomic():
            # Serialize same-customer subscription attempts where supported.
            from accounts.models import User
            User.objects.select_for_update().get(pk=request.user.pk)
            existing = Subscription.objects.filter(
                customer=request.user,
                plan=plan,
                status__in=['draft', 'quotation', 'confirmed', 'active', 'paused'],
            ).first()
            if existing:
                messages.info(request, 'You already have an open subscription for this plan.')
                return redirect('my_subscription_detail', pk=existing.pk)
            today = timezone.now().date()
            subscription = Subscription(
                customer=request.user,
                plan=plan,
                start_date=today,
                status='quotation',
                payment_terms='prepaid',
                created_by=request.user,
            )

            # Set expiry date from plan if available
            if plan.end_date:
                subscription.expiry_date = plan.end_date

            # Calculate next billing date
            subscription.save()
            subscription.next_billing_date = subscription._calculate_next_billing_date(today)
            subscription.save(update_fields=['next_billing_date'])

        messages.success(
            request,
            f'You have successfully subscribed! '
            f'Your subscription number is {subscription.subscription_number}.'
        )
        return redirect('my_subscription_detail', pk=subscription.pk)

    return render(request, 'subscriptions/subscribe_confirm.html', {
        'plan': plan,
    })


@role_required('customer')
def my_subscriptions(request):
    """Customer portal – list only their own subscriptions."""
    all_subscriptions = Subscription.objects.filter(
        customer=request.user
    ).select_related('plan', 'plan__product', 'plan__product__owner').order_by('-created_at')
    subscriptions = all_subscriptions
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        subscriptions = subscriptions.filter(status='active')
    elif status_filter == 'pending':
        subscriptions = subscriptions.filter(status__in=['draft', 'quotation', 'confirmed'])
    elif status_filter == 'closed':
        subscriptions = subscriptions.filter(status='closed')

    return render(request, 'subscriptions/my_subscriptions.html', {
        'subscriptions': subscriptions,
        'status_filter': status_filter or '',
        'active': 'subscriptions',
    })


@role_required('customer')
def customer_product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.select_related('owner').prefetch_related('plans'),
        pk=pk,
        is_active=True,
        approval_status=Product.APPROVAL_APPROVED,
    )
    product.available_plans = [plan for plan in product.plans.all() if plan.is_available]
    return render(request, 'subscriptions/customer_product_detail.html', {
        'product': product,
        'active': 'products',
    })


@role_required('customer')
def my_subscription_detail(request, pk):
    """Customer views their own subscription detail."""
    subscription = get_object_or_404(
        Subscription.objects.select_related(
            'plan', 'plan__product', 'plan__product__owner', 'created_by'
        ),
        pk=pk,
        customer=request.user  # SECURITY: ensure ownership
    )

    # Available upgrade/downgrade plans
    available_plans = Plan.objects.filter(
        is_active=True,
        product__is_active=True,
        product__approval_status='approved',
    ).exclude(pk=subscription.plan.pk).select_related('product', 'product__owner')
    available_plans = [p for p in available_plans if p.is_available and (not p.product_id or p.product.is_active)]

    return render(request, 'subscriptions/my_subscription_detail.html', {
        'subscription': subscription,
        'available_plans': available_plans,
        'active': 'subscriptions',
    })


@role_required('customer')
def customer_cancel_subscription(request, pk):
    """Customer cancels their own subscription."""
    subscription = get_object_or_404(
        Subscription,
        pk=pk,
        customer=request.user  # SECURITY: ensure ownership
    )

    if request.method == 'POST':
        if not subscription.is_closable:
            messages.error(request, 'This subscription cannot be closed.')
            return redirect('my_subscription_detail', pk=pk)

        try:
            subscription.transition_to('closed')
            messages.success(request, 'Your subscription has been cancelled.')
        except ValueError as e:
            messages.error(request, str(e))

    return redirect('my_subscription_detail', pk=pk)


@role_required('customer')
def customer_pause_subscription(request, pk):
    """Customer pauses their subscription."""
    subscription = get_object_or_404(
        Subscription,
        pk=pk,
        customer=request.user
    )

    if request.method == 'POST':
        if not subscription.is_pausable:
            messages.error(request, 'This subscription cannot be paused.')
            return redirect('my_subscription_detail', pk=pk)

        try:
            subscription.transition_to('paused')
            messages.success(request, 'Your subscription has been paused.')
        except ValueError as e:
            messages.error(request, str(e))

    return redirect('my_subscription_detail', pk=pk)


@role_required('customer')
def customer_resume_subscription(request, pk):
    """Customer resumes a paused subscription."""
    subscription = get_object_or_404(
        Subscription,
        pk=pk,
        customer=request.user
    )

    if request.method == 'POST':
        if subscription.status != 'paused':
            messages.error(request, 'This subscription is not paused.')
            return redirect('my_subscription_detail', pk=pk)

        try:
            with transaction.atomic():
                subscription.transition_to('active')
            messages.success(request, 'Your subscription has been resumed.')
        except ValueError as e:
            messages.error(request, str(e))

    return redirect('my_subscription_detail', pk=pk)


@role_required('customer')
def customer_change_plan(request, pk):
    """Customer upgrades or downgrades their subscription plan."""
    subscription = get_object_or_404(
        Subscription,
        pk=pk,
        customer=request.user
    )

    if subscription.status not in ('active', 'confirmed'):
        messages.error(request, 'Can only change plans on active or confirmed subscriptions.')
        return redirect('my_subscription_detail', pk=pk)

    if request.method == 'POST':
        new_plan_id = request.POST.get('new_plan_id')
        if not new_plan_id:
            messages.error(request, 'Please select a new plan.')
            return redirect('my_subscription_detail', pk=pk)

        new_plan = get_object_or_404(Plan, pk=new_plan_id)

        if not new_plan.product_id or not new_plan.is_available or not new_plan.product.is_customer_available:
            messages.error(request, 'The selected plan is not available.')
            return redirect('my_subscription_detail', pk=pk)

        with transaction.atomic():
            old_plan_name = subscription.plan.name
            subscription.plan = new_plan
            # Recalculate next billing date based on new plan
            today = timezone.now().date()
            subscription.next_billing_date = subscription._calculate_next_billing_date(today)
            if new_plan.end_date:
                subscription.expiry_date = new_plan.end_date
            subscription.save()

        messages.success(
            request,
            f'Plan changed from "{old_plan_name}" to "{new_plan.name}".'
        )

    return redirect('my_subscription_detail', pk=pk)
