from django.urls import path
from . import views

urlpatterns = [
    # Admin / Staff subscription management
    path('subscriptions/', views.subscription_list, name='subscription_list'),
    path('subscriptions/create/', views.subscription_create, name='subscription_create'),
    path('subscriptions/<int:pk>/', views.subscription_detail, name='subscription_detail'),
    path('subscriptions/<int:pk>/edit/', views.subscription_edit, name='subscription_edit'),
    path('subscriptions/<int:pk>/confirm/', views.subscription_confirm, name='subscription_confirm'),
    path('subscriptions/<int:pk>/activate/', views.subscription_activate, name='subscription_activate'),
    path('subscriptions/<int:pk>/close/', views.subscription_close, name='subscription_close_admin'),

    # Customer pricing and subscription
    path('pricing/', views.pricing_page, name='pricing_page'),
    path('browse-products/', views.pricing_page, name='customer_products'),
    path('browse-products/<int:pk>/', views.customer_product_detail, name='customer_product_detail'),
    path('pricing/subscribe/<int:plan_id>/', views.subscribe_to_plan, name='subscribe_to_plan'),

    # Customer self-service
    path('my-subscriptions/', views.my_subscriptions, name='my_subscriptions'),
    path('my-subscriptions/<int:pk>/', views.my_subscription_detail, name='my_subscription_detail'),
    path('my-subscriptions/<int:pk>/cancel/', views.customer_cancel_subscription, name='customer_cancel_subscription'),
    path('my-subscriptions/<int:pk>/pause/', views.customer_pause_subscription, name='customer_pause_subscription'),
    path('my-subscriptions/<int:pk>/resume/', views.customer_resume_subscription, name='customer_resume_subscription'),
    path('my-subscriptions/<int:pk>/change-plan/', views.customer_change_plan, name='customer_change_plan'),
]
