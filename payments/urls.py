from django.urls import path
from . import views

urlpatterns = [path('invoices/<int:invoice_pk>/payments/create/', views.payment_create, name='payment_create')]
