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
from django.contrib.auth import logout

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
        messages.success(request, f'Dear {user}, please go to your email {to_email} inbox and click on \
            received activation link to confirm and complete the registration. Note: Check your spam folder.')
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
            user = suform.save(commit=False)
            user.is_acive = False 
            user.save()
            activateEmail(request, user, suform.cleaned_data.get('email'))
            choice = suform.cleaned_data["profile_choice"]
            phone_number = suform.cleaned_data["phone_number"]
            request.session["profile_choice"] = choice 
            request.session["temp_phone"] = phone_number
            return redirect('home')
        else : 
             for error in list(suform.errors.values()):
                messages.error(request, error)

            

    suform = SignUpForm()
    return render(request, "accounts/signup.html", {"form": suform})


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        choice = request.session.get("profile_choice")
        phone_number = request.session.get("temp_phone")
        messages.success(request, 'Thank you for your email confirmation. Now you can continue profile creation .')
        if choice == "customer":
                CustomerProfile.objects.create(user=user, phone_number=phone_number)
                return redirect("customerdashboard")
        elif choice == "provider" or choice == "both":
                request.session["temp_user_id"] = user.id
                return redirect("profile_creation", n=choice)

    else:
        messages.error(request, 'Activation link is invalid!')
    
    return redirect('homepage')






@login_required(login_url="/login/")
def password_change(request):
    user = request.user
    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your password has been changed")
            return redirect('login')
        else:
            for error in list(form.errors.values()):
                messages.error(request, error)

    form = SetPasswordForm(user)
    return render(request, 'accounts/password_reset_confirm.html', {'form': form})




@login_required(login_url="/login/")
def userprofile(request):
    me = User.objects.get(id=request.user.id)
    my_provider_profile = ProviderProfile.objects.filter(user=me).first()
    my_customer_profile = CustomerProfile.objects.filter(user=me).first()
    if request.method == "POST":
        if request.POST.get("modifyprofile"):
            return redirect("modifyprofile")
        if request.POST.get("deleteaccount"):
            messages.warning(request , "All your data will be lost . Are you sure you wish to delete your account ? ")
            return redirect("deleteaccount")
        
    return render(request , "accounts/userprofile.html" ,{"me": me , "my_provider": my_provider_profile, "my_customer": my_customer_profile})



@login_required(login_url ="/login/")
def modifyprofile(request):
    provider_profile = ProviderProfile.objects.filter(user=request.user).first()
    if request.method == "POST":
        form = ProviderForm(request.POST, instance=provider_profile)
        if form.is_valid():
            form.save()
          

            
            messages.success(request,"Details changed successfully ")
            return redirect("userprofile")
        else:
            messages.warning(request, form.errors)
            return redirect("modifyprofile")
    else :

        form = ProviderForm(instance=provider_profile)
    
    return render(request, "accounts/modifyprofile.html", {"form": form })



@login_required(login_url="/login/")
def deleteaccount(request):
    if request.method == "POST":
        request.user.delete()

        logout(request)
        messages.info(request , " Account deleted successfully ")
        return redirect('home')
    return render(request, "accounts/deleteaccount.html")