from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from .forms import SetPasswordForm
from django.contrib.auth.decorators import login_required
from main.forms import ProviderForm

from main.models import CustomerProfile, ProviderProfile

from .forms import SignUpForm
from .tokens import account_activation_token


# Create your views here.
def activateEmail(request, user, to_email):
    mail_subject = 'Activate your user account.'
    message = render_to_string('accounts/template_activate_account.html', {
        'user': user.username,
        'domain': get_current_site(request).domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
        'protocol': 'https' if request.is_secure() else 'http'
    })
    email = EmailMessage(mail_subject, message, to=[to_email])
    if email.send():
        messages.success(request, f'Dear <b>{user}</b>, please go to your email <b>{to_email}</b> inbox and click on \
            received activation link to confirm and complete the registration. <b>Note:</b> Check your spam folder.')
    else:
        messages.error(request, f'Problem sending confirmation email to {to_email}, check if you typed it correctly.')


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
                CustomerProfile.objects.create(user=user, phone_number=phone_number)
                return redirect("customerdashboard")
            elif choice == "provider" or choice == "both":
                request.session["temp_user_id"] = user.id
                request.session["temp_phone"] = suform.cleaned_data["phone_number"]
                return redirect("profile_creation", n=choice)

    suform = SignUpForm()
    return render(request, "accounts/signup.html", {"form": suform})
