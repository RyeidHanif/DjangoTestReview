from django.shortcuts import redirect, render

from main.models import CustomerProfile, ProviderProfile

from .forms import SignUpForm

# Create your views here.


def signup(request):
    '''
    create new user object and send user to profile creation system
    
    the view uses the user creation form to create a user object , 
    use the profile choice given in the form to redirect the user according
    to their choice :
    - for customer : creates a customer profile object in place .
    - for provider or both : redirects user to profile creation view. 

    adds 2 items to the session which will be sent to the profile creation view 
    - phone number to prevent repettion 
    - user id  so that the user can be identified in the profile view (since not logged in )
    '''

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
