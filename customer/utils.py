from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.timezone import (
    get_current_timezone,
    localdate,
    localtime,
    make_aware,
    activate,
    now,
)

from main.models import Appointment, ProviderProfile
from main.utils import get_calendar_service

activate(get_current_timezone())


def get_available_slots(provider, slot_range):

    service = get_calendar_service(provider)
    tz = get_current_timezone()
    today = localdate()
    current_datetime = now()

    duration = provider.providerprofile.duration_mins
    start_time = provider.providerprofile.start_time
    end_time = provider.providerprofile.end_time

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
                cursor = slot_end

            if cursor < busy_end:
                cursor = busy_end

        while (day_end - cursor).total_seconds() >= duration * 60:
            slot_end = cursor + timedelta(minutes=duration)
            available_slots.append((cursor, slot_end))
            cursor = slot_end

    return available_slots


def create_calendar_appointment(start_date, end_date, summary, attendee_email):
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

    return event


def check_appointment_exists(customer, provider):
    return not Appointment.objects.filter(
        customer=customer,
        provider=provider,
        status__in=["pending", "approved"]
    ).exists()
