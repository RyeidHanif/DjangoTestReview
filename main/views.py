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
        return redirect("providerdashboard")
    elif hasattr(user , "customerprofile"):
        return redirect("customerdashboard")
    elif hasattr(user , "providerprofile"):
        return redirect("providerdashboard")


@login_required(login_url='/login/')
def profile_creation(request):
    '''
    profile creation system which uses the provider form and parameter n to divide choices 

    user id and phone number are use from the session and then deleted 
    n is used to differentiate between users who want to be both and those 
    who want to be a provider 
    if n is given as "both" , then a customer profile for that user is also created 
    the user is then redirected to the login page 
    '''
  
    if request.method == "POST":
        provider_form = ProviderForm(request.POST)
        if provider_form.is_valid():

            user = request.user

            if ProviderProfile.objects.filter(user=user).exists():
                return redirect("providerdashboard")

            profile = provider_form.save(commit=False)
            profile.user = user
            profile.phone_number = user.customerprofile.phone_number
            profile.save()

            return redirect("redirectiondashboard")

    provider_form = ProviderForm()
    return render(request, "main/profile_creation.html", {"form": provider_form})
