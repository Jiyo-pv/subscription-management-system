from django.shortcuts import render, redirect
from .forms import SignupForm


def signup(request):

    if request.method == 'POST':
        form = SignupForm(request.POST)

        if form.is_valid():
            user = form.save()
            return redirect('login')

    else:
        form = SignupForm()

    return render(request, 'accounts/signup.html', {
        'form': form
    })
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm



def login_view(request):

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request, user)

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
from django.http import HttpResponse
from .decorators import role_required


@role_required('admin')
def admin_test(request):
    return HttpResponse("You are an ADMIN!")