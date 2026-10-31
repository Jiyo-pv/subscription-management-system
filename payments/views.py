from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from billing.models import Invoice
from .forms import PaymentForm
from .services import record_payment


@role_required('admin', 'staff')
def payment_create(request, invoice_pk):
    invoice = get_object_or_404(Invoice, pk=invoice_pk)
    if invoice.status != Invoice.OPEN:
        messages.error(request, 'Payments can only be recorded for open invoices.')
        return redirect('invoice_detail', pk=invoice.pk)
    form = PaymentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            record_payment(invoice, recorded_by=request.user, **form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, 'Payment recorded.')
            return redirect('invoice_detail', pk=invoice.pk)
    return render(request, 'payments/payment_form.html', {'form': form, 'invoice': invoice})
