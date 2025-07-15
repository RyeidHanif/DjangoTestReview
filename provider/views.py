from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.timezone import (activate, get_current_timezone, localdate,
                                   localtime, make_aware, now)

from main.models import Appointment, ProviderProfile
from main.utils import get_calendar_service

from .forms import AvailabilityForm
from .utils import (EmailCancelledAppointment, EmailConfirmedAppointment,
                    EmailDeclinedAppointment)

activate("Asia/Karachi")


# Create your views here.
from django.shortcuts import redirect, render


@login_required(login_url="/login/")
def providerdashboard(request):
    if request.method == "POST":
        if request.POST.get("myprofile"):
            return redirect("userprofile")
        if request.POST.get("viewanalytics"):
            return redirect("viewanalytics")
        if request.POST.get("viewmyappointments"):
            return redirect("view_my_appointments")
        if request.POST.get("viewpendingappointments"):
            return redirect("view_pending_appointments")
        if request.POST.get("myavailability"):
            return redirect("myavailability")

    return render(request, "provider/providerdashboard.html")


@login_required(login_url="/login/")
def view_my_appointments(request):
    my_appointments = Appointment.objects.filter(
        provider=request.user, status="accepted"
    ).order_by("-date_added")
    if request.method == "POST":
        if request.POST.get("cancel"):
            cancel_appointment = Appointment.objects.get(id=request.POST.get("cancel"))
            to_email = cancel_appointment.customer.email
            customer = cancel_appointment.customer
            provider = cancel_appointment.provider
            cancel_appointment.status = "cancelled"
            service = get_calendar_service(request.user)
            service.events().delete(
                calendarId="primary", eventId=cancel_appointment.event_id
            ).execute()
            cancel_appointment.save()

            EmailCancelledAppointment(request, customer, provider, to_email)
            return redirect("view_my_appointments")

        if request.POST.get("markcompleted"):
            appointment = Appointment.objects.get(id=request.POST.get("markcompleted"))
            current_datetime = now()
            if appointment.date_start > current_datetime:
                messages.warning(
                    request,
                    "This appointment has not happened yet . you cannot mark it complete",
                )
                return redirect("view_my_appointments")
            else:
                appointment.status = "completed"
                appointment.save()
                messages.success(request, "marked successfully")
                return redirect("view_my_appointments")

    return render(
        request, "provider/view_my_appointments.html", {"appointments": my_appointments}
    )


@login_required(login_url="/login/")
def view_pending_appointments(request):
    my_appointments = Appointment.objects.filter(
        provider=request.user, status="pending"
    )
    if request.method == "POST":
        if request.POST.get("reject"):
            appointment = Appointment.objects.get(id=request.POST.get("reject"))
            service = get_calendar_service(request.user)
            service.events().delete(calendarId="primary", eventId=appointment.event_id)
            appointment.status = "rejected"
            EmailDeclinedAppointment(
                request,
                appointment.customer,
                appointment.provider,
                "N/A",
                to_email=appointment.customer.email,
            )
            appointment.save()
            messages.success(request, " appointment rejected successfully")
            return redirect("view_pending_appointments")
        if request.POST.get("accept"):
            appointment = Appointment.objects.get(id=request.POST.get("accept"))
            appointment.status = "accepted"
            appointment.save()
            EmailConfirmedAppointment(
                request,
                appointment.customer,
                appointment.provider,
                localtime(appointment.date_start),
                localtime(appointment.date_end),
                to_email=appointment.customer.email,
            )
            messages.success(request, "Accepted successflly ")
            return redirect("view_pending_appointments")

    return render(
        request,
        "provider/view_pending_appointments.html",
        {"appointments": my_appointments},
    )


def viewanalytics(request):
    pass


def myavailability(request):

    tz = "Asia/Karachi"

    if request.method == "POST":
        form = AvailabilityForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data["start_date"]
            end_date = form.cleaned_data["end_date"]
            start_time = form.cleaned_data["start_time"]
            end_time = form.cleaned_data["end_time"]
            cause = form.cleaned_data["cause"]
            start_datetime = make_aware(
                datetime.combine(start_date, start_time), timezone=tz
            )
            end_datetime = make_aware(datetime.combine(end_date, end_time), timezone=tz)
            start_datetime_iso = start_datetime.isoformat()
            end_datetime_iso = end_datetime.isoformat()
            service = get_calendar_service(request.user)
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
            return redirect("myavailability")

    else:
        form = AvailabilityForm()

    return render(request, "provider/myavailability.html", {"form": form})
