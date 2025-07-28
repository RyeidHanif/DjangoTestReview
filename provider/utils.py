from datetime import datetime, time, timedelta, timezone

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.timezone import (activate, get_current_timezone, localdate,
                                   localtime, make_aware, now)
from googleapiclient.errors import HttpError

from main.models import Appointment, ProviderProfile


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


def EmailCancelledAppointment(
    request,
    customer,
    provider,
    to_email,
):
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
