from django.contrib import admin
from .models import Subscription, SubscriptionLine


class SubscriptionLineInline(admin.TabularInline):
    model = SubscriptionLine
    extra = 0


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'subscription_number', 'customer', 'plan',
        'status', 'start_date', 'expiry_date', 'created_at'
    )
    list_filter = ('status', 'plan')
    search_fields = ('subscription_number', 'customer__name', 'customer__email')
    inlines = [SubscriptionLineInline]
    readonly_fields = ('subscription_number', 'created_at', 'updated_at')


@admin.register(SubscriptionLine)
class SubscriptionLineAdmin(admin.ModelAdmin):
    list_display = ('subscription', 'description', 'quantity', 'unit_price')
