from django.shortcuts import redirect, render

from main.models import CustomerProfile, ProviderProfile

from .forms import SignUpForm

# Create your views here.


def signup(request):

    if request.method == "POST":
        suform = SignUpForm(request.POST)
        if suform.is_valid():
            user = suform.save()
            choice = suform.cleaned_data["profile_choice"]
            phone_number = suform.cleaned_data["phone_number"]
            if choice == "customer":
                if ProviderProfile.objects.filter(user=user).exists():
                    return redirect("login")
                CustomerProfile.objects.create(user=user, phone_number=phone_number)
                return redirect("login")
            elif choice == "provider" or choice == "both":
                request.session["temp_user_id"] = user.id
                request.session["temp_phone"] = suform.cleaned_data["phone_number"]
                return redirect("profile_creation", n=choice)

    suform = SignUpForm()
    return render(request, "accounts/signup.html", {"form": suform})
