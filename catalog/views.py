from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.decorators import role_required
from .models import Product, Plan
from .forms import ProductForm, PlanForm, ProductReviewForm


@role_required('product_owner')
def product_owner_dashboard(request):
    from subscriptions.models import Subscription
    products = Product.objects.filter(owner=request.user)
    plans = Plan.objects.filter(product__owner=request.user)
    stats = {
        'products_total': products.count(),
        'products_pending': products.filter(approval_status__in=['pending', 'changes_requested']).count(),
        'products_approved': products.filter(approval_status='approved').count(),
        'products_rejected': products.filter(approval_status='rejected').count(),
        'plans_total': plans.count(),
        'plans_active': plans.filter(is_active=True).count(),
        'subscriptions_total': Subscription.objects.filter(plan__product__owner=request.user).count(),
    }
    cards = [
        ('Total Products', stats['products_total'], '▣', '/products/'),
        ('Pending Approval', stats['products_pending'], '◷', '/products/?approval=pending'),
        ('Approved Products', stats['products_approved'], '✓', '/products/?approval=approved'),
        ('Rejected Products', stats['products_rejected'], '!', '/products/?approval=rejected'),
        ('Total Plans', stats['plans_total'], '◈', '/plans/'),
        ('Active Pricing Plans', stats['plans_active'], '↻', '/plans/?status=active'),
        ('Subscriptions', stats['subscriptions_total'], '◇', '/subscriptions/'),
    ]
    return render(request, 'catalog/product_owner_dashboard.html', {
        'stats': stats,
        'cards': cards,
        'recent_products': products.order_by('-submitted_at')[:8],
        'active': 'dashboard',
    })


@role_required('admin', 'product_owner')
def product_list(request):
    products = Product.objects.select_related('owner').all()
    if request.user.role == 'product_owner':
        products = products.filter(owner=request.user)

    search = request.GET.get('q', '').strip()
    product_type = request.GET.get('type', '')
    status = request.GET.get('status', '')
    approval = request.GET.get('approval', '')
    if search:
        products = products.filter(Q(name__icontains=search) | Q(description__icontains=search))
    if product_type:
        products = products.filter(product_type=product_type)
    if status in ('active', 'inactive'):
        products = products.filter(is_active=(status == 'active'))
    if approval:
        products = products.filter(approval_status=approval)

    return render(request, 'catalog/product_list.html', {
        'products': products,
        'search': search,
        'current_type': product_type,
        'current_status': status,
        'current_approval': approval,
        'approval_choices': Product.APPROVAL_STATUS_CHOICES,
        'type_choices': Product.TYPE_CHOICES,
        'active': 'products',
    })


@role_required('product_owner')
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.owner = request.user
            product.approval_status = Product.APPROVAL_PENDING
            product.approval_feedback = ''
            product.approved_at = None
            product.submitted_at = timezone.now()
            product.save()
            messages.success(request, 'Product submitted for admin approval.')
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'catalog/product_form.html', {
        'form': form, 'title': 'Add product', 'submit_label': 'Submit for approval',
    })


@role_required('product_owner')
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save(commit=False)
            product.approval_status = Product.APPROVAL_PENDING
            product.approval_feedback = ''
            product.approved_at = None
            product.submitted_at = timezone.now()
            product.save()
            messages.success(request, 'Changes submitted for admin approval.')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'catalog/product_form.html', {
        'form': form, 'product': product, 'title': 'Edit and resubmit product', 'submit_label': 'Save and resubmit',
    })


@role_required('admin', 'product_owner')
def product_detail(request, pk):
    filters = {'pk': pk}
    if request.user.role == 'product_owner':
        filters['owner'] = request.user
    product = get_object_or_404(Product.objects.select_related('owner'), **filters)
    return render(request, 'catalog/product_detail.html', {
        'product': product,
        'variants': product.variants.all(),
        'plans': product.plans.all(),
    })


@role_required('product_owner')
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk, owner=request.user)
    if product.plans.exists():
        messages.error(request, 'Products with plans cannot be deleted. Deactivate the plans first.')
        return redirect('product_detail', pk=pk)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted.')
        return redirect('product_list')
    return render(request, 'catalog/product_confirm_delete.html', {'product': product})


@role_required('admin')
def product_toggle_active(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.is_active = not product.is_active
        product.save(update_fields=['is_active', 'updated_at'])
        state = 'activated' if product.is_active else 'deactivated'
        messages.success(request, f'Product {state}.')
    return redirect('product_list')


@role_required('admin')
def product_review(request, pk, action):
    product = get_object_or_404(Product, pk=pk)
    if action not in ('approve', 'reject', 'request-changes'):
        raise PermissionDenied
    if request.method == 'GET':
        return render(request, 'catalog/product_review.html', {
            'product': product, 'action': action,
            'form': ProductReviewForm(initial={'owner': product.owner_id}),
        })
    if request.method != 'POST':
        raise PermissionDenied
    form = ProductReviewForm(request.POST)
    form.data = request.POST.copy()
    form.data['action'] = action.replace('-', '_')
    if not form.is_valid():
        return render(request, 'catalog/product_review.html', {
            'product': product, 'action': action, 'form': form,
        }, status=400)
    if form.cleaned_data.get('owner'):
        product.owner = form.cleaned_data['owner']
    if action == 'approve':
        product.approval_status = Product.APPROVAL_APPROVED
        product.approval_feedback = ''
        product.approved_at = timezone.now()
        message = 'Product approved and eligible for customer listings.'
    elif action == 'reject':
        product.approval_status = Product.APPROVAL_REJECTED
        product.approval_feedback = form.cleaned_data['feedback'].strip()
        product.approved_at = None
        message = 'Product rejected. The owner can update and resubmit it.'
    else:
        product.approval_status = Product.APPROVAL_CHANGES_REQUESTED
        product.approval_feedback = form.cleaned_data['feedback'].strip()
        product.approved_at = None
        message = 'Changes requested from the product owner.'
    product.save()
    messages.success(request, message)
    return redirect('product_detail', pk=pk)


@role_required('admin', 'product_owner')
def plan_list(request):
    plans = Plan.objects.select_related('product', 'product__owner').all()
    if request.user.role == 'product_owner':
        plans = plans.filter(product__owner=request.user)
    search = request.GET.get('q', '').strip()
    billing = request.GET.get('billing', '')
    status = request.GET.get('status', '')
    owner_id = request.GET.get('owner', '')
    if search:
        plans = plans.filter(Q(name__icontains=search) | Q(product__name__icontains=search))
    if billing:
        plans = plans.filter(billing_period=billing)
    if status in ('active', 'inactive'):
        plans = plans.filter(is_active=(status == 'active'))
    if request.user.role == 'admin' and owner_id:
        plans = plans.filter(product__owner_id=owner_id)
    from accounts.models import User
    return render(request, 'catalog/plan_list.html', {
        'plans': plans, 'search': search, 'current_billing': billing,
        'current_status': status, 'current_owner': owner_id,
        'billing_choices': Plan.BILLING_PERIOD_CHOICES,
        'owners': User.objects.filter(role='product_owner'), 'active': 'plans',
    })


@role_required('product_owner')
def plan_create(request):
    if request.method == 'POST':
        form = PlanForm(request.POST, owner=request.user)
        if form.is_valid():
            plan = form.save(commit=False)
            if plan.product.owner_id != request.user.pk or not plan.product.is_customer_available:
                raise PermissionDenied
            plan.save()
            messages.success(request, 'Pricing plan created.')
            return redirect('plan_list')
    else:
        form = PlanForm(owner=request.user)
    return render(request, 'catalog/plan_form.html', {
        'form': form, 'title': 'Create plan', 'submit_label': 'Create plan',
    })


@role_required('product_owner')
def plan_edit(request, pk):
    plan = get_object_or_404(Plan.objects.select_related('product'), pk=pk, product__owner=request.user)
    if request.method == 'POST':
        form = PlanForm(request.POST, instance=plan, owner=request.user)
        if form.is_valid():
            updated = form.save(commit=False)
            if updated.product.owner_id != request.user.pk or not updated.product.is_customer_available:
                raise PermissionDenied
            updated.save()
            messages.success(request, 'Pricing plan updated.')
            return redirect('plan_list')
    else:
        form = PlanForm(instance=plan, owner=request.user)
    return render(request, 'catalog/plan_form.html', {
        'form': form, 'plan': plan, 'title': f'Edit {plan.name}', 'submit_label': 'Save changes',
    })


@role_required('admin', 'product_owner')
def plan_detail(request, pk):
    filters = {'pk': pk}
    if request.user.role == 'product_owner':
        filters['product__owner'] = request.user
    plan = get_object_or_404(Plan.objects.select_related('product', 'product__owner'), **filters)
    subscriptions = plan.subscriptions.select_related('customer').all()[:10]
    return render(request, 'catalog/plan_detail.html', {'plan': plan, 'subscriptions': subscriptions})


@role_required('product_owner')
def plan_delete(request, pk):
    plan = get_object_or_404(Plan, pk=pk, product__owner=request.user)
    if plan.subscriptions.exists():
        messages.error(request, 'Plans with subscriptions cannot be deleted.')
        return redirect('plan_detail', pk=pk)
    if request.method == 'POST':
        plan.delete()
        messages.success(request, 'Pricing plan deleted.')
        return redirect('plan_list')
    return render(request, 'catalog/plan_confirm_delete.html', {'plan': plan})


@role_required('admin', 'product_owner')
def plan_toggle_active(request, pk):
    filters = {'pk': pk}
    if request.user.role == 'product_owner':
        filters['product__owner'] = request.user
    plan = get_object_or_404(Plan.objects.select_related('product'), **filters)
    if request.method == 'POST':
        if request.user.role == 'admin':
            if plan.is_active:
                plan.is_active = False
            else:
                messages.error(request, 'Only the Product Owner can activate this plan.')
                return redirect('plan_list')
        else:
            if not plan.product.is_customer_available and not plan.is_active:
                messages.error(request, 'The product must be approved before its plan can be activated.')
                return redirect('plan_list')
            plan.is_active = not plan.is_active
        plan.save(update_fields=['is_active', 'updated_at'])
        messages.success(request, 'Plan availability updated.')
    return redirect('plan_list')
