from django.contrib import admin

from .models import Invoice, InvoiceLine


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'customer', 'subscription', 'due_date', 'status')
    list_filter = ('status',)
    search_fields = ('invoice_number', 'customer__email', 'subscription__subscription_number')
    inlines = [InvoiceLineInline]
