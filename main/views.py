from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from .forms import ProviderForm
from .models import CustomerProfile, ProviderProfile
from django.contrib import messages

# Create your views here.


def home(request):
    '''
    display the homepage
    '''
    return render(request, "main/home.html")


@login_required(login_url = "/login/")
def redirectiondashboard(request):
    user = request.user 
    if hasattr(user, 'customerprofile' ) and hasattr(user , 'providerprofile'):
        return render(request , "main/redirectdashboard.html")
    elif hasattr(user , "customerprofile"):
        return redirect("customerdashboard")
    elif hasattr(user , "providerprofile"):
        return redirect("providerdashboard")
    messages.error(request , "you do not have a profile , please create one ")
    
    return redirect("signup")
    


def profile_creation(request, n):
    '''
    profile creation system which uses the provider form and parameter n to divide choices 

    user id and phone number are use from the session and then deleted 
    n is used to differentiate between users who want to be both and those 
    who want to be a provider 
    if n is given as "both" , then a customer profile for that user is also created 
    the user is then redirected to the login page 
    '''
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
