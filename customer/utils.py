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

activate("Asia/Karachi")


def check_appointment_exists(customer, provider):
    """
    Used to check if an appointment exists between a customer and a provider which is currently in the works
    this is done to prevent one customer from having multiple simultaneous appointments with the same provider
    return False if appointment Exists 
    return True if appointment does not Exist
    """
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
    """
    Send an Email from the customer to the provider requesting them to accept the new rescheduled version of the appointment
    """

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
    """
    Sends an email from the customer to the provider to tell them that a new appointment has been created
    """
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
    """
    This Function calculates the total price for an appointment , whether it be recurring or simple
    First checks the pricing model of the provider which can either be hourly or fixed
    in the case of hourly , performs a calculation to change the price according to the time of the appointment
    if there is recurrence in the appointment , it calculated the total price by finding out the
    number of recurrences and multiplying that by the price previously calculated for all 3 recurrence types
    """
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
    """
    Creates and Saves a new appointment. it has been separated to prevent repetition and shorten the AddAppointment view
    """
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


def change_and_save_appointment(
    request,
    appointment,
    recurrence_frequency,
    until_date,
    start_datetime,
    end_datetime,
    total_price,
):
    """
    Used in the AddAppointmentview in the case that the appointment is being rescheduled
    """
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
