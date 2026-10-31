from django.db.models import Prefetch

from catalog.models import Plan, Product


def get_public_products():
    """Return every active, approved product with its eligible active plans."""
    products = Product.objects.filter(
        is_active=True,
        approval_status=Product.APPROVAL_APPROVED,
    ).select_related('owner').prefetch_related(Prefetch(
        'plans',
        queryset=Plan.objects.filter(is_active=True).select_related('product').order_by('price'),
        to_attr='listed_plans',
    ))
    available = []
    for product in products:
        product.available_plans = [plan for plan in product.listed_plans if plan.is_available]
        available.append(product)
    return available
