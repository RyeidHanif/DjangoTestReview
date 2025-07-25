# Standard library
import os
from datetime import datetime, time, timedelta, timezone

# Third-party (Google API libs)
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError

# Django
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Permission
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.timezone import (
    activate,
    get_current_timezone,
    localdate,
    localtime,
    make_aware,
    now,
)

# Local app imports
from .forms import ProviderForm
from .models import (
    ProviderProfile,
    User,
)
from main.models import Appointment, ProviderProfile


class GoogleCalendarClient:
    def __init__(self):
        self.clientID = os.getenv("client_id")
        self.clientSecret = os.getenv("client_secret")

    def get_calendar_service(self, user):
        """function to load user credentials and refresh them if required

        returns an object which is used to perform CRUD operations on events in the calendar
        usually referred to as service
        """
        profile = ProviderProfile.objects.get(user=user)
        creds = Credentials(
            token=profile.google_access_token,
            refresh_token=profile.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.clientID,
            client_secret=self.clientSecret,
            scopes=["https://www.googleapis.com/auth/calendar"],
        )

        # Try refreshing only if token expired
        if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                profile.google_access_token = creds.token
                profile.google_refresh_token = creds.refresh_token
                profile.google_token_expiry = creds.expiry
                profile.save()
            
        return build("calendar", "v3", credentials=creds)

    def create_auth_url(self):
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

        return auth_url

    def get_available_slots(self, provider, slot_range):

        service = self.get_calendar_service(provider)
        tz = get_current_timezone()
        today = localdate()
        current_datetime = now()

        duration = provider.providerprofile.duration_mins
        start_time = provider.providerprofile.start_time
        end_time = provider.providerprofile.end_time
        buffer = provider.providerprofile.buffer

        available_slots = []

        for day in range(slot_range):
            day_start = make_aware(
                datetime.combine(today + timedelta(days=day), start_time), timezone=tz
            )
            day_end = make_aware(
                datetime.combine(today + timedelta(days=day), end_time), timezone=tz
            )

            if day == 0:

                if current_datetime + timedelta(minutes=duration) > day_start:
                    day_start = current_datetime + timedelta(minutes=duration)

            if day_start >= day_end:
                continue

            events = (
                service.freebusy()
                .query(
                    body={
                        "timeMin": day_start.isoformat(),
                        "timeMax": day_end.isoformat(),
                        "timeZone": "Asia/Karachi",
                        "items": [{"id": "primary"}],
                    }
                )
                .execute()
            )

            busy_times = events["calendars"]["primary"]["busy"]

            cursor = day_start

            for i in range(len(busy_times)):
                busy_start = datetime.fromisoformat(busy_times[i]["start"])
                busy_end = datetime.fromisoformat(busy_times[i]["end"])

                while (busy_start - cursor).total_seconds() >= duration * 60:
                    slot_end = cursor + timedelta(minutes=duration)
                    available_slots.append((cursor, slot_end))
                    cursor = slot_end + timedelta(minutes=buffer)

                if cursor < busy_end:
                    cursor = busy_end

            while (day_end - cursor).total_seconds() >= duration * 60:
                slot_end = cursor + timedelta(minutes=duration)
                available_slots.append((cursor, slot_end))
                cursor = slot_end + timedelta(minutes=buffer)

        return available_slots

    def create_calendar_appointment(
        self,
        start_date,
        end_date,
        summary,
        attendee_email,
        recurrence_frequency,
        until_date,
    ):
        event = {
            "summary": summary,
            "location": "My Office ",
            "description": "Appointment",
            "start": {
                "dateTime": start_date,
                "timeZone": "Asia/Karachi",
            },
            "end": {
                "dateTime": end_date,
                "timeZone": "Asia/Karachi",
            },
            "attendees": [
                {"email": attendee_email},
            ],
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 24 * 60},
                    {"method": "email", "minutes": 20},
                    {"method": "popup", "minutes": 10},
                ],
            },
        }
        if recurrence_frequency not in [None, "NONE"] and until_date != None:

            until_date = until_date  # Replace with your form field
            until_utc = datetime.combine(until_date, time.min).replace(
                tzinfo=timezone.utc
            )
            until_str = until_utc.strftime("%Y%m%dT%H%M%SZ")
            recur = f"RRULE:FREQ={recurrence_frequency};UNTIL={until_str}"
            event["recurrence"] = [recur]

        return event

    def reschedule_google_event(self,user ,  event_id, new_start, new_end , recurrence_frequency , recurrence_until):
        service = self.get_calendar_service(user)
        event = service.events().get(calendarId="primary", eventId=event_id).execute()
        event["start"]["dateTime"] = new_start
        event["end"]["dateTime"] = new_end
        
        if recurrence_frequency and recurrence_until:
            until_utc = datetime.combine(recurrence_until, time.min).replace(tzinfo=timezone.utc)
            until_str = until_utc.strftime('%Y%m%dT%H%M%SZ')
            event["recurrence"] = [f"RRULE:FREQ={recurrence_frequency};UNTIL={until_str}"]
        else:
            event.pop("recurrence", None)

        return service.events().update(calendarId="primary", eventId=event_id, body=event).execute()

    def create_google_calendar_event(
        self,
        provider,
        timeslot,
        summary,
        attendee_email,
        recurrence_frequency,
        until_date,
    ):
        event_body = self.create_calendar_appointment(
            timeslot[0],
            timeslot[1],
            summary,
            attendee_email,
            recurrence_frequency,
            until_date,
        )
        service = self.get_calendar_service(provider)
        return (
            service.events()
            .insert(calendarId="primary", body=event_body, sendUpdates="all")
            .execute()
        )

    def google_calendar_callback(self, request):
        flow = Flow.from_client_secrets_file(  # load google auth client credentils
            "credentials.json",
            scopes=["https://www.googleapis.com/auth/calendar"],
            redirect_uri="http://127.0.0.1:8000/google/oauth2callback/",
        )

        flow.fetch_token(
            authorization_response=request.build_absolute_uri()
        )  # exchange the auth code for tokens

        creds = (
            flow.credentials
        )  # credentials object which contains the tokens and expiry
        profile = ProviderProfile.objects.get(user=request.user)
        profile.google_access_token = creds.token
        profile.google_refresh_token = creds.refresh_token
        profile.google_token_expiry = creds.expiry
        profile.google_calendar_connected = True
        profile.save()
        messages.success(request, "Your Google Calendar is successfully connected!")
    
    def delete_event(self, user, event_id):
        service = self.get_calendar_service(user)
        service.events().delete(
                calendarId="primary", eventId=event_id
            ).execute()
        
    def create_availability_block(self, request , user ,cause , start_datetime_iso , end_datetime_iso ):
            service = self.get_calendar_service(user)
            event = {
                "summary": "Unavailable",
                "location": "NA",
                "description": cause,
                "start": {
                    "dateTime": start_datetime_iso,
                    "timeZone": "Asia/Karachi",
                },
                "end": {
                    "dateTime": end_datetime_iso,
                    "timeZone": "Asia/Karachi",
                },
                "reminders": {
                    "useDefault": True,
                },
            }
            service.events().insert(calendarId="primary", body=event).execute()
            messages.success(request, "Added time block successfully")
        
