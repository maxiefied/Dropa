from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import SignupForm


def signup(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Your account is ready.")
            return redirect("accounts:dashboard")
    else:
        form = SignupForm()

    return render(request, "accounts/signup.html", {"form": form})


@login_required
def dashboard(request):
    return render(request, "accounts/dashboard.html")
