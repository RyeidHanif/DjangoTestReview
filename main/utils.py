# extra utility functions needed for e.g refrehsing tokens ,getting calender service
import json
import os
from datetime import datetime, timedelta

from django.core.exceptions import (FieldError, ObjectDoesNotExist,
                                    PermissionDenied, ValidationError)
from django.db.utils import IntegrityError, OperationalError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.timezone import (activate, get_current_timezone, localdate,
                                   localtime, make_aware, now)
from dotenv import load_dotenv
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .models import Appointment, ProviderProfile

load_dotenv()


def cancellation(request, user, appointment):
    """Checks whether a useer has cancelled 3 or more appointments withint the last 30 days"""
    cutoff_date = now() - timedelta(days=30)
    appointment_date = appointment.date_start.astimezone(get_current_timezone())
    appointment.cancelled_by = user
    appointment.cancelled_at = now()
    cancel_date = appointment.cancelled_at.astimezone(get_current_timezone())
    if appointment_date - cancel_date < timedelta(hours=12):
        appointment.bad_cancel = True
        appointment.save()
    cancelled_count = Appointment.objects.filter(
        cancelled_by=user,
        date_start__gte=cutoff_date,
        status="cancelled",
        bad_cancel=True,
    ).count()
    return cancelled_count


def force_provider_calendar(provider):
    """Once the refresh token of a provider expired, forces the provider to reconnect to thecalendar"""
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
        return JsonResponse(
            {"error": exc.message_dict if hasattr(exc, "message_dict") else str(exc)},
            status=400,
        )

    if isinstance(exc, PermissionDenied):
        return JsonResponse(
            {"error": "permission_denied", "message": str(exc)}, status=403
        )

    if isinstance(exc, Http404) or isinstance(exc, ObjectDoesNotExist):
        return JsonResponse({"error": "not_found", "message": str(exc)}, status=404)

    if isinstance(exc, FieldError):
        return JsonResponse({"error": "field_error", "message": str(exc)}, status=400)

    if isinstance(exc, IntegrityError):
        return JsonResponse(
            {"error": "integrity_error", "message": str(exc)}, status=400
        )

    if isinstance(exc, OperationalError):
        return JsonResponse(
            {"error": "database_error", "message": "Database error occurred."},
            status=500,
        )

    return JsonResponse({"error": "unknown_error", "message": str(exc)}, status=500)
