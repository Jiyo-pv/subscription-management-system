from django.urls import path

from . import views

urlpatterns = [
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('subscriptions/<int:subscription_pk>/invoices/create/', views.invoice_create, name='invoice_create'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/mark-paid/', views.invoice_mark_paid, name='invoice_mark_paid'),
]
