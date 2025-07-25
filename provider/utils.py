from django.contrib import messages
from django.core.mail import EmailMessage
from datetime import datetime, time, timedelta, timezone
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
from main.utils import get_calendar_service

tz = str(get_current_timezone())


def create_calendar_appointment(
    start_date,
    end_date,
    summary,
    attendee_email,
    recurrence_frequency,
    until_date,
    appointment,
):
    event = {
        "summary": summary,
        "location": "My Office ",
        "description": "Appointment",
        "start": {
            "dateTime": start_date,
            "timeZone": tz,
        },
        "end": {
            "dateTime": end_date,
            "timeZone": tz,
        },
        "attendees": [],
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

        until_utc = datetime.combine(until_date, time.min).replace(tzinfo=timezone.utc)
        until_str = until_utc.strftime("%Y%m%dT%H%M%SZ")
        recur = f"RRULE:FREQ={recurrence_frequency};UNTIL={until_str}"
        event["recurrence"] = [recur]

    customer_pref = appointment.customer.notification_settings.preferences
    provider_pref = appointment.provider.notification_settings.preferences

    if customer_pref != "none":
        event["attendees"].append({"email": attendee_email})

    if provider_pref == "none":
        event["reminders"] = {"useDefault": False, "overrides": []}

    return event


def EmailConfirmedAppointment(
    request,
    customer,
    provider,
    date_start,
    date_end,
    to_email,
):
    mail_subject = "Appointment confirmed"
    message = f"""Dear {customer.username} You have been allotted the slot from {date_start} To {date_end} with provider : {provider} . Please do not miss the appointment . You will recieve reminder emails before the appointment as well .
     """

    email = EmailMessage(mail_subject, message, to=[to_email])
    SendEmail(request , email , to_email , provider)


def EmailDeclinedAppointment(
    request,
    customer,
    provider,
    reason,
    to_email,
):
    mail_subject = "Appointment Declined"
    message = f"Dear {customer.username}  , Unfortunately Mr.{provider} could not accept your appointment request, "
    email = EmailMessage(mail_subject, message, to=[to_email])
    SendEmail(request , email , to_email , provider)


def EmailCancelledAppointment(
    request,
    customer,
    provider,
    to_email,
):
    mail_subject = "Appointment Cancelled "
    message = f"Dear {customer.username}  , Unfortunately Mr.{provider} has had to cancel the  appointment ."
    email = EmailMessage(mail_subject, message, to=[to_email])
    SendEmail(request , email , to_email , provider)



def create_google_calendar_event(
    service,
    timeslot,
    summary,
    attendee_email,
    recurrence_frequency,
    until_date,
    appointment,
):
    event_body = create_calendar_appointment(
        timeslot[0],
        timeslot[1],
        summary,
        attendee_email,
        recurrence_frequency,
        until_date,
        appointment,
    )
    return (
        service.events()
        .insert(calendarId="primary", body=event_body, sendUpdates="all")
        .execute()
    )


def reschedule_google_event(
    service, event_id, new_start, new_end, recurrence_frequency, recurrence_until
):
    event = service.events().get(calendarId="primary", eventId=event_id).execute()
    event["start"]["dateTime"] = new_start
    event["end"]["dateTime"] = new_end

    if recurrence_frequency and recurrence_until:
        until_utc = datetime.combine(recurrence_until, time.min).replace(
            tzinfo=timezone.utc
        )
        until_str = until_utc.strftime("%Y%m%dT%H%M%SZ")
        event["recurrence"] = [f"RRULE:FREQ={recurrence_frequency};UNTIL={until_str}"]
    else:
        event.pop("recurrence", None)

    return (
        service.events()
        .update(calendarId="primary", eventId=event_id, body=event)
        .execute()
    )


def SendEmailRescheduleAccepted(
    request,
    customer,
    provider,
    date_start,
    date_end,
    to_email,
):
    mail_subject = "Reschedule Approved "
    message = f"Dear {customer.username} You have been allotted the slot from {date_start} To {date_end} with provider : {provider} . Please do not miss the appointment . You will recieve reminder emails before the appointment as well.  "
    email = EmailMessage(mail_subject, message, to=[to_email])
    SendEmail(request , email , to_email , provider)
  


def EmailRescheduleDeclined(
    request,
    customer,
    provider,
    date_start,
    date_end,
    to_email,
):
    mail_subject = "Reschedule Declined  "
    message = f"Dear {customer.username} Your Alloted slot from  {date_start} To {date_end} with provider : {provider} Has been Declined . The appointment has been removed . Please act accordingly. "
    email = EmailMessage(mail_subject, message, to=[to_email])
    SendEmail(request , email , to_email , provider)
    



# used to remove repetition , this function is used in all the above email sending functions 
def SendEmail(request , email , to_email , provider):
    if email.send():
        messages.success(
            request,
            f"Dear {provider.username}, your email has been sent to the customer . please prepare for the appointment accordingly ",
        )
    else:
        messages.error(
            request,
            f"Problem sending confirmation email to {to_email}, check if you typed it correctly.",
        )

