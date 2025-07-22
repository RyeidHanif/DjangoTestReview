# extra utility functions needed for e.g refrehsing tokens ,getting calender service
import json
from datetime import datetime, timedelta

from django.utils.timezone import (
    activate,
    get_current_timezone,
    localdate,
    localtime,
    make_aware,
    now,
)
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .models import Cancellation, ProviderProfile

from dotenv import load_dotenv

import os

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

    # Try refreshing only if token expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            profile.google_access_token = creds.token
            profile.google_refresh_token = creds.refresh_token
            profile.google_token_expiry = creds.expiry
            profile.save()
        except RefreshError:
            # Refresh token is invalid — handle re-auth here
            profile.google_access_token = None
            profile.google_refresh_token = None
            profile.google_token_expiry = None
            profile.google_calendar_connected = False
            profile.save()
            raise Exception(
                "Google Calendar token expired. Please reconnect your calendar."
            )

    return build("calendar", "v3", credentials=creds)


def cancellation(user, appointment):
    cutoff_date = now() - timedelta(days=30)

    appointment_date = appointment.date_start.astimezone(get_current_timezone())
    cancel_date = now()
    if appointment_date - cancel_date < timedelta(hours=12):
        cancelled = Cancellation.objects.create(user=user, appointment=appointment)

    count__recent_cancelled = Cancellation.objects.filter(
        user=user, cancelled_at__gte=cutoff_date
    ).count()
    return count__recent_cancelled
