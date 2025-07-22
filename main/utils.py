# extra utility functions needed for e.g refrehsing tokens ,getting calender service
import json
import os

from django.utils.timezone import now
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .models import ProviderProfile

# Load environment variables from the .env file
load_dotenv()


with open("credentials.json", "r") as f:
    data = json.load(f)
    clientID = os.getenv("client_id")
    clientSecret = os.getenv("client_secret")


def get_calendar_service(user):
    """function to load user credentials and refresh them if required

    returns an object which is used to perform CRUD operations on events in the calendar
    usually referred to as service
    """
    profile = ProviderProfile.objects.get(user=user)
    creds = Credentials(
        token=profile.google_access_token,
        refresh_token=profile.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=clientID,
        client_secret=clientSecret,
        scopes=["https://www.googleapis.com/auth/calendar"],
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        profile.google_access_token = creds.token
        profile.google_refresh_token = creds.refresh_token
        profile.google_token_expiry = creds.expiry
        profile.save()

    return build("calendar", "v3", credentials=creds)
