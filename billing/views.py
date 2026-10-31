from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import role_required
from subscriptions.models import Subscription

from .forms import InvoiceCreateForm
from .models import Invoice
from .services import create_invoice_for_subscription


def _visible_invoices(user):
    invoices = Invoice.objects.select_related('customer', 'subscription', 'subscription__plan', 'subscription__plan__product').prefetch_related('lines')
    if user.role == 'product_owner':
        return invoices.filter(subscription__plan__product__owner=user)
    return invoices


@role_required('admin', 'staff', 'product_owner')
def invoice_list(request):
    invoices = _visible_invoices(request.user)
    status = request.GET.get('status', '')
    if status in dict(Invoice.STATUS_CHOICES):
        invoices = invoices.filter(status=status)
    if request.GET.get('outstanding') == '1':
        invoices = invoices.filter(status=Invoice.OPEN, amount_paid__lt=models.F('total_amount'))
    if request.GET.get('overdue') == '1':
        invoices = invoices.filter(
            status=Invoice.OPEN,
            due_date__lt=timezone.localdate(),
            amount_paid__lt=models.F('total_amount'),
        )
    page_obj = Paginator(invoices, 25).get_page(request.GET.get('page'))
    return render(request, 'billing/invoice_list.html', {
        'invoices': page_obj.object_list, 'page_obj': page_obj,
        'status_choices': Invoice.STATUS_CHOICES, 'current_status': status,
        'outstanding_only': request.GET.get('outstanding') == '1',
        'overdue_only': request.GET.get('overdue') == '1',
        'active': 'invoices',
    })


@role_required('admin', 'staff')
def invoice_create(request, subscription_pk):
    subscription = get_object_or_404(Subscription.objects.select_related('customer', 'plan'), pk=subscription_pk)
    if subscription.status not in ('confirmed', 'active', 'paused'):
        messages.error(request, 'Invoices can only be created for confirmed, active, or paused subscriptions.')
        return redirect('subscription_detail', pk=subscription.pk)
    form = InvoiceCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        invoice = create_invoice_for_subscription(subscription, **form.cleaned_data)
        if invoice is None:
            messages.info(request, 'An invoice already exists for this billing period.')
            return redirect('invoice_list')
        messages.success(request, f'Invoice {invoice.invoice_number} created.')
        return redirect('invoice_detail', pk=invoice.pk)
    return render(request, 'billing/invoice_form.html', {'form': form, 'subscription': subscription})


def _get_invoice_for_user(user, pk):
    if user.role == 'customer':
        return get_object_or_404(Invoice.objects.select_related('subscription', 'subscription__plan', 'subscription__plan__product').prefetch_related('lines'), pk=pk, customer=user)
    if user.role in ('admin', 'staff', 'product_owner'):
        return get_object_or_404(_visible_invoices(user), pk=pk)
    raise Http404


@role_required('admin', 'staff', 'product_owner', 'customer')
def invoice_detail(request, pk):
    return render(request, 'billing/invoice_detail.html', {'invoice': _get_invoice_for_user(request.user, pk), 'active': 'invoices'})
