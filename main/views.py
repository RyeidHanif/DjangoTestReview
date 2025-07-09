from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from .forms import ProviderForm
from .models import CustomerProfile, ProviderProfile

# Create your views here.


def home(request):
    return render(request, "main/home.html")


@login_required(login_url="/login/")
def dashboard(request):
    return render(request, "main/dashboard.html")


def profile_creation(request, n):
    user_id = request.session.get("temp_user_id")
    phone = request.session.get("temp_phone")
    if not user_id:
        return redirect("signup")
    if request.method == "POST":
        provider_form = ProviderForm(request.POST)
        if provider_form.is_valid():

            user = User.objects.get(id=user_id)

            if ProviderProfile.objects.filter(user=user).exists():
                return redirect("login")

            profile = provider_form.save(commit=False)
            profile.user = user
            profile.phone_number = phone
            profile.save()

            del request.session["temp_user_id"]
            del request.session["temp_phone"]
            if n == "both":
                CustomerProfile.objects.create(user=user, phone_number=phone)
            return redirect("login")

    provider_form = ProviderForm()
    return render(request, "main/profile_creation.html", {"form": provider_form})
