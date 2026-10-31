from django.urls import path
from .views import admin_test, admin_dashboard, customer_detail, customer_list, customer_invoices, customer_profile, product_owner_list, product_owner_profile, toggle_product_owner_active, create_staff, customer_portal, health, signup, login_view, logout_view, home
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('signup/', signup, name='signup'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('', home, name='home'),
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/customers/', customer_list, name='customer_list'),
    path('admin-dashboard/customers/<int:pk>/', customer_detail, name='customer_detail'),
    path('admin-dashboard/product-owners/', product_owner_list, name='product_owner_list'),
    path('admin-dashboard/product-owners/<int:pk>/toggle/', toggle_product_owner_active, name='toggle_product_owner_active'),
    path('owner-profile/', product_owner_profile, name='product_owner_profile'),
    path('admin-test/', admin_test, name='admin_test'),
    path('create-staff/', create_staff, name='create_staff'),
    path('customer-portal/', customer_portal, name='customer_portal'),
    path('customer-profile/', customer_profile, name='customer_profile'),
    path('my-invoices/', customer_invoices, name='customer_invoices'),

    path(
    'password-reset/',
    auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='accounts/password_reset_email.html',
        subject_template_name='accounts/password_reset_subject.txt',
        success_url='/password-reset/done/'
    ),
    name='password_reset'
),

path(
    'password-reset/done/',
    auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ),
    name='password_reset_done'
),

path(
    'reset/<uidb64>/<token>/',
    auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html'
    ),
    name='password_reset_confirm'
),

path(
    'reset/done/',
    auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ),
    name='password_reset_complete'
),
path('health/', health, name='health')
]
