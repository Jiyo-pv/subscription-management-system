from django.contrib import admin
from .models import Discount, Product, ProductVariant, Plan, Tax


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'product_type', 'approval_status', 'is_active', 'submitted_at')
    list_filter = ('product_type', 'approval_status', 'is_active')
    search_fields = ('name', 'owner__name', 'owner__email')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('name', 'product', 'sales_price', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'product__name')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'product', 'price', 'billing_period', 'is_active')
    list_filter = ('billing_period', 'is_active')
    search_fields = ('name', 'product__name')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Tax)
class TaxAdmin(admin.ModelAdmin):
    list_display = ('name', 'percent', 'is_active')
    list_filter = ('is_active',)


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ('name', 'discount_type', 'value', 'apply_to', 'times_used', 'usage_limit', 'is_active')
    list_filter = ('discount_type', 'apply_to', 'is_active')
    filter_horizontal = ('products',)
