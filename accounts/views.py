from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from main.forms import ProviderForm
from main.models import (CustomerProfile, NotificationPreferences,
                         ProviderProfile)

from .forms import (ChangeNotificationPreferencesForm, ProfilePhotoForm,
                    SetPasswordForm, SignUpForm)
from .tokens import account_activation_token


# Create your views here.
def activateEmail(request, user, to_email):
    mail_subject = "Activate your user account."
    message = render_to_string(
        "accounts/template_activate_account.html",
        {
            "user": user.username,
            "domain": get_current_site(request).domain,
            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": account_activation_token.make_token(user),
            "protocol": "https" if request.is_secure() else "http",
        },
    )
    email = EmailMessage(mail_subject, message, to=[to_email])
    if email.send():
        messages.success(
            request,
            f"Dear {user}, please go to your email {to_email} inbox and click on \
            received activation link to confirm and complete the registration. Note: Check your spam folder.",
        )
    else:
        messages.error(
            request,
            f"Problem sending confirmation email to {to_email}, check if you typed it correctly.",
        )


def signup(request):
    """
    create new user object and send user to profile creation system

    the view uses the user creation form to create a user object ,
    use the profile choice given in the form to redirect the user according
    to their choice :
    - for customer : creates a customer profile object in place .
    - for provider or both : redirects user to profile creation view.

    adds 2 items to the session which will be sent to the profile creation view
    - phone number to prevent repettion
    - user id  so that the user can be identified in the profile view (since not logged in )
    """

    if request.method == "POST":
        suform = SignUpForm(request.POST)
        if suform.is_valid():
            user = suform.save(commit=False)
            user.is_acive = False
            user.save()
            activateEmail(request, user, suform.cleaned_data.get("email"))
            choice = suform.cleaned_data["profile_choice"]
            phone_number = suform.cleaned_data["phone_number"]
            request.session["profile_choice"] = choice
            request.session["temp_phone"] = phone_number
            return redirect("home")
        else:
            for error in list(suform.errors.values()):
                messages.error(request, error)

    suform = SignUpForm()
    return render(request, "accounts/signup.html", {"form": suform})


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        choice = request.session.get("profile_choice")
        phone_number = request.session.get("temp_phone")
        messages.success(
            request,
            "Thank you for your email confirmation. Now you can continue profile creation .",
        )
        if choice == "customer":
            CustomerProfile.objects.create(user=user, phone_number=phone_number)
            return redirect("customer_dashboard")
        elif choice == "provider" or choice == "both":
            request.session["temp_user_id"] = user.id
            return redirect("profile_creation", n=choice)

    else:
        messages.error(request, "Activation link is invalid!")

    return redirect("home")


@login_required(login_url="/login/")
def password_change(request):
    user = request.user
    if request.method == "POST":
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your password has been changed")
            return redirect("login")
        else:
            for error in list(form.errors.values()):
                messages.error(request, error)

    form = SetPasswordForm(user)
    return render(request, "accounts/password_reset_confirm.html", {"form": form})


@login_required(login_url="/login/")
def user_profile(request):

    me = User.objects.get(id=request.user.id)
    my_provider_profile = ProviderProfile.objects.filter(user=me).first()
    my_customer_profile = CustomerProfile.objects.filter(user=me).first()
    change_profile_form = None
    if my_provider_profile:
        change_profile_form = ProfilePhotoForm(
            request.POST or None, request.FILES or None, instance=my_provider_profile
        )
    if request.method == "POST":
        if request.POST.get("changenot"):
            notiform = ChangeNotificationPreferencesForm(request.POST)
            if notiform.is_valid():
                preference = notiform.cleaned_data["preferences"]
                obj, created = NotificationPreferences.objects.get_or_create(
                    user=request.user
                )
                obj.preferences = preference
                obj.save()

        if request.POST.get("modify_profile"):
            return redirect("modify_profile")
        if request.POST.get("delete_account"):
            messages.warning(
                request,
                "All your data will be lost . Are you sure you wish to delete your account ? ",
            )
            return redirect("delete_account")

        if request.POST.get("change_pfp"):
            if change_profile_form.is_valid():
                change_profile_form.save()
                messages.success(request, "changed successfuly")
        elif request.POST.get("remove_pfp") and my_provider_profile:
            my_provider_profile.profile_photo.delete(save=True)
            messages.success(request, "Profile picture removed.")
            return redirect("user_profile")

    user_pref = NotificationPreferences.objects.filter(user=request.user).first()
    notiform = ChangeNotificationPreferencesForm(instance=user_pref)

    return render(
        request,
        "accounts/user_profile.html",
        {
            "me": me,
            "my_provider": my_provider_profile,
            "my_customer": my_customer_profile,
            "form": notiform,
            "change_profile_form": change_profile_form,
        },
    )


@login_required(login_url="/login/")
def modify_profile(request):
    provider_profile = ProviderProfile.objects.filter(user=request.user).first()
    if request.method == "POST":
        form = ProviderForm(request.POST, instance=provider_profile)
        if form.is_valid():
            form.save()

            messages.success(request, "Details changed successfully ")
            return redirect("user_profile")
        else:
            messages.warning(request, form.errors)
            return redirect("modify_profile")
    else:

        form = ProviderForm(instance=provider_profile)

    return render(request, "accounts/modify_profile.html", {"form": form})


@login_required(login_url="/login/")
def delete_account(request):
    if request.method == "POST":
        request.user.delete()

        logout(request)
        messages.info(request, " Account deleted successfully ")
        return redirect("home")
    return render(request, "accounts/delete_account.html")
