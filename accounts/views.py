from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponse, JsonResponse
import time
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

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 300  # 5 minutes


def login_view(request):
    now = time.time()

    failed_attempts = request.session.get('login_failed_attempts', 0)
    lockout_until = request.session.get('login_lockout_until')

    # Check whether the user is currently locked out
    if lockout_until and now < lockout_until:
        remaining = int(lockout_until - now)

        form = AuthenticationForm(request)

        form.add_error(
            None,
            f"Too many failed login attempts. "
            f"Please try again in {max(1, remaining // 60 + 1)} minute(s)."
        )

        return render(request, 'accounts/login.html', {
            'form': form
        })

    # Lockout period has expired
    if lockout_until and now >= lockout_until:
        request.session.pop('login_failed_attempts', None)
        request.session.pop('login_lockout_until', None)

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            # Successful login → reset failed attempts
            request.session.pop('login_failed_attempts', None)
            request.session.pop('login_lockout_until', None)

            user = form.get_user()
            login(request, user)

            if user.role == 'customer':
                return redirect('customer_portal')

            return redirect('home')

        else:
            # Failed login
            failed_attempts += 1
            request.session['login_failed_attempts'] = failed_attempts

            if failed_attempts >= MAX_LOGIN_ATTEMPTS:
                request.session['login_lockout_until'] = (
                    now + LOCKOUT_SECONDS
                )

                form.add_error(
                    None,
                    "Too many failed login attempts. "
                    "Please try again in 5 minutes."
                )

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