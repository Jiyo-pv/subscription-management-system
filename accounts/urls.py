from django.urls import path
from .views import admin_test, create_staff, signup, login_view, logout_view, home

urlpatterns = [
    path('signup/', signup, name='signup'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('', home, name='home'),
    path('admin-test/', admin_test, name='admin_test'),
    path('create-staff/', create_staff, name='create_staff'),
]