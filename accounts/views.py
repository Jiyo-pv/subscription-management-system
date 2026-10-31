from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse

from .forms import SignupForm, StaffCreationForm
from .decorators import role_required


def health(request):
    return JsonResponse({
        'status': 'ok'
    })


def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('login')

    else:
        form = SignupForm()

    return render(request, 'accounts/signup.html', {
        'form': form
    })


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request, user)

            if user.role == 'customer':
                return redirect('customer_portal')

            return redirect('home')

    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {
        'form': form
    })


def logout_view(request):
    logout(request)
    return redirect('login')


def home(request):
    return render(request, 'accounts/home.html')


@role_required('admin')
def admin_test(request):
    return HttpResponse("You are an ADMIN!")


@role_required('admin')
def create_staff(request):
    if request.method == 'POST':
        form = StaffCreationForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('home')

    else:
        form = StaffCreationForm()

    return render(
        request,
        'accounts/create_staff.html',
        {'form': form}
    )


@role_required('customer')
def customer_portal(request):
    return render(
        request,
        'accounts/customer_portal.html'
    )