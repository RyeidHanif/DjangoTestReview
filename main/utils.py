# extra utility functions needed for e.g refrehsing tokens ,getting calender service
import json

from django.utils.timezone import now
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime , timedelta 
from django.utils.timezone import (activate, get_current_timezone, localdate,
                                   localtime, make_aware, now)
from google.auth.exceptions import RefreshError
from django.core.exceptions import ValidationError, PermissionDenied, ObjectDoesNotExist, FieldError
from django.http import JsonResponse
from django.db.utils import IntegrityError, OperationalError
from django.http import Http404
from django.shortcuts import get_object_or_404



from .models import ProviderProfile, Appointment

with open("credentials.json", "r") as f:
    data = json.load(f)

    clientID = data["web"]["client_id"]
    clientSecret = data["web"]["client_secret"]


def get_calendar_service(user):
    """function to load user credentials and refresh them if required

    returns an object which is used to perform CRUD operations on events in the calendar
    usually referred to as service
    """
    profile = get_object_or_404(ProviderProfile, user=user)
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
            raise Exception("Google Calendar token expired. Please reconnect your calendar.")

    return build("calendar", "v3", credentials=creds)



def cancellation(request,  user , appointment):
    cutoff_date = now() - timedelta(days=30)
    appointment_date = appointment.date_start.astimezone(get_current_timezone())
    appointment.cancelled_by = user
    appointment.cancelled_at = now()
    cancel_date =appointment.cancelled_at.astimezone(get_current_timezone())
    if appointment_date - cancel_date < timedelta(hours=12):
        appointment.bad_cancel = True
        appointment.save()
    cancelled_count = Appointment.objects.filter(cancelled_by = user , date_start__gte=cutoff_date , status = "cancelled" ,bad_cancel = True ).count()
    return cancelled_count



def force_provider_calendar(provider):
    profile = ProviderProfile.objects.get(user=provider)
    profile.google_access_token = None
    profile.google_refresh_token = None
    profile.google_token_expiry = None
    profile.google_calendar_connected = False
    profile.save()




def handle_exception(exc):
    """
    Given an exception, return a JsonResponse with a suitable error message and status code.
    Optionally pass `provider` to handle RefreshError with calendar re-auth logic.
    """
    

    if isinstance(exc, ValidationError):
        return JsonResponse({"error": exc.message_dict if hasattr(exc, 'message_dict') else str(exc)}, status=400)

    if isinstance(exc, PermissionDenied):
        return JsonResponse({"error": "permission_denied", "message": str(exc)}, status=403)

    if isinstance(exc, Http404) or isinstance(exc, ObjectDoesNotExist):
        return JsonResponse({"error": "not_found", "message": str(exc)}, status=404)

    if isinstance(exc, FieldError):
        return JsonResponse({"error": "field_error", "message": str(exc)}, status=400)

    if isinstance(exc, IntegrityError):
        return JsonResponse({"error": "integrity_error", "message": str(exc)}, status=400)

    if isinstance(exc, OperationalError):
        return JsonResponse({"error": "database_error", "message": "Database error occurred."}, status=500)

    return JsonResponse({"error": "unknown_error", "message": str(exc)}, status=500)
