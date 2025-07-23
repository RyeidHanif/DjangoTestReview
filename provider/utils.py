from django.contrib import messages
from django.core.mail import EmailMessage
from datetime import datetime, time, timedelta, timezone 

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.timezone import (activate, get_current_timezone, localdate,
                                   localtime, make_aware, now)

from main.models import Appointment, ProviderProfile
from main.utils import get_calendar_service
from googleapiclient.errors import HttpError


def create_calendar_appointment(start_date, end_date, summary, attendee_email ,recurrence_frequency , until_date, appointment):
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
    if recurrence_frequency not in [None , "NONE"] and until_date != None :
       
        until_utc = datetime.combine(until_date, time.min).replace(tzinfo=timezone.utc)
        until_str = until_utc.strftime('%Y%m%dT%H%M%SZ')
        recur = f"RRULE:FREQ={recurrence_frequency};UNTIL={until_str}"
        event["recurrence"] = [recur]
    
    customer_pref = appointment.customer.notification_settings.preferences
    provider_pref = appointment.provider.notification_settings.preferences
   
    if customer_pref != "none":
        event["attendees"].append({"email": attendee_email})

    if provider_pref == "none":
        event["reminders"] = {
            "useDefault": False,
            "overrides": []
        }
    

    return event
def EmailConfirmedAppointment(
    request, customer, provider, date_start, date_end, to_email,
):
    mail_subject = "Appointment confirmed"
    message = f'''Dear {customer.username} You have been allotted the slot from {date_start} To {date_end} with provider : {provider} . Please do not miss the appointment . You will recieve reminder emails before the appointment as well .
     '''
    
    email = EmailMessage(mail_subject, message, to=[to_email])
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


def EmailDeclinedAppointment(request, customer, provider, reason, to_email,  ):
    mail_subject = "Appointment Declined"
    message = f"Dear {customer.username}  , Unfortunately Mr.{provider} could not accept your appointment request, "
    email = EmailMessage(mail_subject, message, to=[to_email])
    if email.send():
        messages.success(
            request,
            f"Dear {provider.username} The email has been sent to the customer . please do not reject appointments unnecessarily or otherwise block that time slot  ",
        )
    else:
        messages.error(
            request,
            f"Problem sending confirmation email to {to_email}, check if you typed it correctly.",
        )


def EmailCancelledAppointment(request, customer, provider, to_email , ):
    mail_subject = "Appointment Cancelled "
    message = f"Dear {customer.username}  , Unfortunately Mr.{provider} has had to cancel the  appointment ."
    email = EmailMessage(mail_subject, message, to=[to_email])
    if email.send():
        messages.success(
            request,
            f"Dear {provider.username} The email has been sent to the customer . please do not cancel appointments unnecessarily  ",
        )
    else:
        messages.error(
            request,
            f"Problem sending confirmation email to {to_email}, check if you typed it correctly.",
        )





def SendEmailRescheduleAccepted(
    request, customer, provider, date_start, date_end, to_email,  
):
    mail_subject = "Reschedule Approved "
    message = f"Dear {customer.username} You have been allotted the slot from {date_start} To {date_end} with provider : {provider} . Please do not miss the appointment . You will recieve reminder emails before the appointment as well.  "
    email = EmailMessage(mail_subject, message, to=[to_email])
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



def EmailRescheduleDeclined(request , customer , provider , date_start , date_end , to_email,  ):
    mail_subject = "Reschedule Declined  "
    message = f"Dear {customer.username} Your Alloted slot from  {date_start} To {date_end} with provider : {provider} Has been Declined . The appointment has been removed . Please act accordingly. "
    email = EmailMessage(mail_subject, message, to=[to_email])
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