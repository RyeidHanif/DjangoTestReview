from datetime import datetime, time, timedelta, timezone

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
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
from googleapiclient.errors import HttpError

from main.models import Appointment, ProviderProfile
from main.utils import get_calendar_service

activate("Asia/Karachi")


def get_available_slots(provider, slot_range):

    service = get_calendar_service(provider)
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
    start_date, end_date, summary, attendee_email, recurrence_frequency, until_date
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

        until_date = datetime(2025, 7, 25).date()  # Replace with your form field
        until_utc = datetime.combine(until_date, time.min).replace(tzinfo=timezone.utc)
        until_str = until_utc.strftime("%Y%m%dT%H%M%SZ")
        recur = f"RRULE:FREQ={recurrence_frequency};UNTIL={until_str}"
        event["recurrence"] = [recur]

    return event


def check_appointment_exists(customer, provider):
    return not Appointment.objects.filter(
        customer=customer,
        provider=provider,
        status__in=["pending", "accepted", "rescheduled"],
    ).exists()


def EmailRescheduledAppointment(
    request,
    customer,
    provider,
    old_date_start,
    old_date_end,
    new_date_start,
    new_date_end,
    to_email,
    special_requests,
):
    mail_subject = "Appointment Reschedule Request"
    message = f"""Dear {provider.username} , Mr. {customer.username} wishes to reschedule the appointment from the original date and time which was
    originally :  {old_date_start} to {old_date_end}   and now shall be : {new_date_start} To {new_date_end} . If you wish to reject  the appointment please do so in your account . dont worry currently, the original date is 
    still there and here are the customer's Specil requests : {special_requests}"""
    email = EmailMessage(mail_subject, message, to=[to_email])
    if email.send():
        messages.success(
            request,
            f"Dear {customer.username} The email has been sent to the provider  . please do not Try to reschedule events unnecessarily as it created a lot of problems   ",
        )
    else:
        messages.error(
            request,
            f"Problem sending confirmation email to {to_email}, check if you typed it correctly.",
        )


def EmailPendingAppointment(
    request, customer, provider, date_start, date_end, to_email, special_requests
):
    mail_subject = "Appointment Created - pending "
    message = f"Dear {provider.username} , {customer.username} has created an appointment with you from  {date_start} To {date_end} . The Status is currently pending . Please accept or reject it in your account  .These are some requests : {special_requests} "
    email = EmailMessage(mail_subject, message, to=[to_email])
    if email.send():
        messages.success(
            request,
            f"Dear {customer.username}, your email has been sent to the Provider . please prepare for the appointment accordingly ",
        )
    else:
        messages.error(
            request,
            f"Problem sending confirmation email to {to_email}, check if you typed it correctly.",
        )


def calculate_total_price(provider, **kwargs):
    start_date = localdate()

    if provider.pricing_model == "hourly":
        price_per_appointment = (int(provider.duration_mins) / 60) * provider.rate
    else:
        price_per_appointment = provider.rate
    occurrences = 1
    if kwargs.get("recurrence_frequency") and kwargs.get("until_date"):
        recurrence_freq = kwargs["recurrence_frequency"]
        recurrence_until = kwargs["until_date"]

        if recurrence_freq == "DAILY":
            occurrences = (recurrence_until - start_date).days + 1
        elif recurrence_freq == "WEEKLY":
            occurrences = ((recurrence_until - start_date).days // 7) + 1
        elif recurrence_freq == "MONTHLY":
            occurrences = (
                (recurrence_until.year - start_date.year) * 12
                + (recurrence_until.month - start_date.month)
                + 1
            )

    return round(occurrences * price_per_appointment, 2)


def create_and_save_appointment(
    customer,
    provider_user,
    start,
    end,
    price,
    special_requests,
    recurrence_frequency,
    until_date,
):
    appointment = Appointment(
        provider=provider_user,
        customer=customer,
        date_start=start,
        date_end=end,
        total_price=price,
        special_requests=special_requests,
        recurrence_frequency=recurrence_frequency,
        recurrence_until=until_date,
    )
    appointment.save()
    return appointment


def create_google_calendar_event(
    service, timeslot, summary, attendee_email, recurrence_frequency, until_date
):
    event_body = create_calendar_appointment(
        timeslot[0],
        timeslot[1],
        summary,
        attendee_email,
        recurrence_frequency,
        until_date,
    )
    return (
        service.events()
        .insert(calendarId="primary", body=event_body, sendUpdates="all")
        .execute()
    )


def reschedule_google_event(service, event_id, new_start, new_end):
    event = service.events().get(calendarId="primary", eventId=event_id).execute()
    event["start"]["dateTime"] = new_start
    event["end"]["dateTime"] = new_end
    return (
        service.events()
        .update(calendarId="primary", eventId=event_id, body=event)
        .execute()
    )


def change_and_save_appointment(
    request,
    appointment,
    recurrence_frequency,
    until_date,
    start_datetime,
    end_datetime,
    total_price,
):
    old_start = appointment.date_start
    old_end = appointment.date_end

    appointment.date_start = start_datetime
    appointment.date_end = end_datetime
    appointment.status = "rescheduled"
    appointment.recurrence_frequency = recurrence_frequency
    appointment.recurrence_until = until_date
    appointment.special_requests = request.POST.get("special_requests", "")
    appointment.total_price = total_price
    appointment.save()

    if appointment.provider.notification_settings.preferences == "all":

        EmailRescheduledAppointment(
            request,
            appointment.customer,
            appointment.provider,
            localtime(old_start),
            localtime(old_end),
            localtime(appointment.date_start),
            localtime(appointment.date_end),
            appointment.provider.email,
            appointment.special_requests,
        )
    return appointment
