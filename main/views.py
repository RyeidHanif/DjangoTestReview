import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Permission, User
from django.shortcuts import redirect, render
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow

from .forms import ProviderForm
from .models import CustomerProfile, ProviderProfile

# Create your views here.


def home(request):
    """
    display the homepage
    """
    return render(request, "main/home.html")


@login_required(login_url="/login/")
def redirectiondashboard(request):
    """temporary dashboard to redirect  different users to their respective places"""
    user = request.user
    if hasattr(user, "customerprofile") and hasattr(user, "providerprofile"):
        return render(request, "main/redirectdashboard.html")
    elif hasattr(user, "customerprofile"):
        return redirect("customerdashboard")
    elif hasattr(user, "providerprofile"):
        return redirect("connect_to_calendar")
    messages.error(request, "you do not have a profile , please create one ")

    return redirect("profile_creation")


def profile_creation(request, n):
    """
    profile creation system which uses the provider form and parameter n to divide choices

    user id and phone number are use from the session and then deleted
    n is used to differentiate between users who want to be both and those
    who want to be a provider
    if n is given as "both" , then a customer profile for that user is also created
    the user is then redirected to the login page
    """
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


@login_required(login_url="/login/")
def connect_to_calendar(request):
    """Displays the page to allow the user to connect to their google calendar"""
    user = request.user
    profile = ProviderProfile.objects.get(user=user)
    if profile.google_calendar_connected:
        messages.info(request, "you are connected to calendar")
        return redirect("providerdashboard")
    else:
        if request.method == "POST":
            return redirect("connect_google")

        return render(request, "main/connect_to_calendar.html")


def connect_google(request):
    """Creates the authorization url which the user is redirected to to allow for the connection"""

    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = (
        "1"  # tell google that no https , using http
    )

    flow = Flow.from_client_secrets_file(  # load google auth clint credentials
        "credentials.json",
        scopes=["https://www.googleapis.com/auth/calendar"],
        redirect_uri="http://127.0.0.1:8000/google/oauth2callback/",
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",  # need it even when user is offline
        include_granted_scopes="true",  # all scopes ,rw
        prompt="consent",  # ask for the consent every time
    )
    return redirect(auth_url)


def oauth2callback(request):
    """authenticates the user ,stores credentials and redirects to dashboard

    google authentication client credentials are loaded from the credentials.json file
    stored in the BASE directory .
    Scopes allotted are full permissions and the redirect uri matches that in
    the google oauth credential settings to allow google to redirect the user back here
    the authorization code sent by google is exchanged for access and refresh tokens
    which are then stored in the ProvideProfile model columns to be used later
    """
    flow = Flow.from_client_secrets_file(  # load google auth client credentils
        "credentials.json",
        scopes=["https://www.googleapis.com/auth/calendar"],
        redirect_uri="http://127.0.0.1:8000/google/oauth2callback/",
    )

    flow.fetch_token(
        authorization_response=request.build_absolute_uri()
    )  # exchange the auth code for tokens

    creds = flow.credentials  # credentials object which contains the tokens and expiry
    profile = ProviderProfile.objects.get(user=request.user)
    profile.google_access_token = creds.token
    profile.google_refresh_token = creds.refresh_token
    profile.google_token_expiry = creds.expiry
    profile.google_calendar_connected = True
    profile.save()
    messages.success(request, "Your Google Calendar is successfully connected!")
    return redirect("providerdashboard")
