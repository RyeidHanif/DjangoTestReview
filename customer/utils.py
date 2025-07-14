from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from main.models import ProviderProfile
from django.contrib.auth.models import User
from django.contrib import messages
from datetime import datetime, time, timedelta
from django.utils.timezone import get_current_timezone, make_aware, localtime, localdate
from main.utils import get_calendar_service
from django.http import HttpResponse
from main.models import Appointment

def get_available_slots(provider, slot_range):
    service = get_calendar_service(provider)
    time_start = provider.providerprofile.start_time
    time_end = provider.providerprofile.end_time
    tz = get_current_timezone()
    today = localdate()
    duration = provider.providerprofile.duration_mins
    current_time = localtime().time()
    current_datetime = make_aware(datetime.combine(today, current_time), timezone=tz)
    available_slots = []

    for day in range(slot_range):
        date = today + timedelta(days=day)
        day_start = make_aware(datetime.combine(date, time_start), timezone=tz)

        day_end = make_aware(datetime.combine(date, time_end), timezone=tz)

        cursor = day_start

        events_today = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=day_start.isoformat(),
                timeMax=day_end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_today.get("items", [])

        event_start_times = [
            datetime.fromisoformat(event["start"]["dateTime"]) for event in events
        ]
        event_end_times = [
            datetime.fromisoformat(event["end"]["dateTime"]) for event in events
        ]

        for i in range(len(event_start_times)):
            event_start = event_start_times[i]
            event_end = event_end_times[i]

            if event_start > cursor and (
                day >= 1 or cursor > (current_datetime + timedelta(minutes=duration))
            ):
                gap = (event_start - cursor).total_seconds() / 60
                if gap >= duration:
                    gap_start = cursor
                    while (event_start - gap_start).total_seconds() / 60 >= duration:
                        slot_end = gap_start + timedelta(minutes=duration)
                        available_slots.append((gap_start, slot_end))
                        gap_start = slot_end

            cursor = max(cursor, event_end)

        if day_end > cursor:
            gap_start = cursor
            while (day_end - gap_start).total_seconds() / 60 >= duration:
                slot_end = gap_start + timedelta(minutes=duration)
                available_slots.append((gap_start, slot_end))
                gap_start = slot_end

    return available_slots


def create_calendar_appointment(start_date, end_date, summary, attendee_email):
    event = {
        "summary": summary ,
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
    appointment = Appointment.objects.filter(customer=customer , provider=provider).first()
    if appointment and ( appointment.status not in ["completed", "rejected"]): 
        return False
    else :
        return True
