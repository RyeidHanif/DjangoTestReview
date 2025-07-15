from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Permission, User
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.timezone import get_current_timezone, localdate, localtime, make_aware

from main.models import Appointment, ProviderProfile
from main.utils import get_calendar_service

from .utils import (
    check_appointment_exists,
    create_calendar_appointment,
    get_available_slots,
    EmailRescheduledAppointment,
)

# Create your views here.


@login_required(login_url="/login/")
def customerdashboard(request):
    if request.method == "POST":
        if request.POST.get("viewproviders"):
            return redirect("viewproviders")
        if request.POST.get("viewappointments"):
            return redirect("viewappointments")
        if request.POST.get("myprofile"):
            return redirect("userprofile")
    return render(request, "customer/customerdashboard.html")


@login_required(login_url="/login/")
def viewproviders(request):
    providers = ProviderProfile.objects.exclude(user=request.user)
    categories = ["doctor", "consultant", "therapist", "counsellor"]
    if request.method == "POST":
        print(
            f"The current provider  at the end of viewproviders function is {ProviderProfile.objects.get(id=request.POST.get("bookappointment")).user.username}"
        )
        messages.info(
            request, "You are being redirected to the service providers schedule"
        )
        return redirect("schedule", providerID=request.POST.get("bookappointment"))

    return render(
        request,
        "customer/viewproviders.html",
        {"providers": providers, "categories": categories},
    )


@login_required(login_url="/login/")
def schedule(request, providerID):

    provider_profile = ProviderProfile.objects.get(id=providerID)
    provider = provider_profile.user
    slot_range = 1

    if request.method == "POST":
        if request.POST.get("week"):
            slot_range = 7
        elif request.POST.get("day"):
            slot_range = 1
        elif request.POST.get("slot_range"):
            slot_range = int(request.POST.get("slot_range"))

        available_slots = get_available_slots(provider, slot_range)

        if request.POST.get("addappointment"):
            index = int(request.POST.get("addappointment"))
            timeslot = available_slots[index]
            request.session["timeslot_tuple"] = (
                timeslot[0].isoformat(),
                timeslot[1].isoformat(),
            )
            print(
                f"The current provider , at the end of scheudle functions is {User.objects.get(id=provider.id).username} "
            )
            return redirect("addappointment", providerUserID=provider.id)

    else:
        available_slots = get_available_slots(provider, slot_range)

    return render(
        request,
        "customer/schedule.html",
        {
            "available_slots": available_slots,
            "provider": provider,
            "slot_range": slot_range,
        },
    )


@login_required(login_url="/login/")
def addappointment(request, providerUserID):
    mode = request.session.get("mode", "normal")
    
    print(f"DEBUG .CURRENT SESSION IS {mode}")
    timeslot = request.session.get("timeslot_tuple", [])
    provider_user = User.objects.get(id=providerUserID)
    provider = ProviderProfile.objects.get(user=provider_user)
    start_datetime = datetime.fromisoformat(timeslot[0])
    end_datetime = datetime.fromisoformat(timeslot[1])
    if provider.pricing_model == "hourly":
        total_price = (int(provider.duration_mins) / 60) * (provider.rate)
    else:
        total_price = provider.rate
    print(f"The current provider is {provider_user.username}")
    customer = request.user

    if mode == "normal":
        print(f"DEBUG. : CURRENT SESSION IS {mode}")

        if not check_appointment_exists(customer, provider_user):
            messages.warning(
                request,
                "You already have an appointment with this provider . please cancel that one to create a new one ",
            )
            return redirect("viewproviders")
        else:

            if request.method == "POST":
                if request.POST.get("confirm"):
                    newappointment = Appointment(
                        provider=provider_user,
                        customer=request.user,
                        date_start=start_datetime,
                        date_end=end_datetime,
                        total_price=total_price,
                    )
                    summary = f"Appointment with {newappointment.customer.username } "
                    attendee_email = newappointment.customer.email
                    event = create_calendar_appointment(
                        timeslot[0], timeslot[1], summary, attendee_email
                    )
                    service = get_calendar_service(provider_user)
                    event = (
                        service.events()
                        .insert(calendarId="primary", body=event, sendUpdates="all")
                        .execute()
                    )
                    event_id = event["id"]
                    newappointment.event_id = event_id
                    newappointment.save()

                    messages.success(request, "Event created successfully ")
                    return redirect("customerdashboard")

            elif request.POST.get("cancel"):
                messages.success(request, "Appointment cancelled successfully ")
                return redirect("customerdashboard")
            





    elif mode == "reschedule":
        print(f"DEBUG CURRENT SESSION IS {mode}")
        appointment = Appointment.objects.filter(
            customer=request.user, provider=provider_user
        ).first()
        appointmentid = appointment.id
        print(f"currnt appointment id is {appointmentid}")
        if request.POST.get("confirm"):
            appointment = Appointment.objects.get(id=appointmentid)
            old_date_start = appointment.date_start
            old_date_end = appointment.date_end
            appointment.date_start = start_datetime
            appointment.date_end = end_datetime
            appointment.save()
            event_id = appointment.event_id
            service = get_calendar_service(appointment.provider)
            event = (
                service.events().get(calendarId="primary", eventId=event_id).execute()
            )
            if event:
                event["start"]["dateTime"] = timeslot[0]
                event["end"]["dateTime"] = timeslot[1]
                service.events().update(
                    calendarId="primary", body=event, eventId=event_id
                ).execute()
                EmailRescheduledAppointment(request , appointment.customer , appointment.provider , localtime(old_date_start) , localtime(old_date_end) , localtime(appointment.date_start) , localtime(appointment.date_end) ,appointment.provider.email) 
                messages.success(request, "Event updated successfully ")
                request.session.pop("mode", None)
                return redirect("viewappointments")
            else:
                messages.error(
                    request, " problem in accessing google calendar,  please try later"
                )
                return redirect("viewappointments")
        elif request.POST.get("cancel"):
            messages.info(request, "the appointment was not changed ")
            return redirect("viewappointments")

    return render(
        request,
        "customer/addappointment.html",
        {"start": start_datetime, "end": end_datetime},
    )


@login_required(login_url="/login/")
def viewappointments(request):
    myappointments = (
        Appointment.objects.filter(customer=request.user).order_by('-date_added')
        .all()
        .exclude(status="rejected")
        .exclude(status="cancelled")
    )
    if request.method == "POST":
        if request.POST.get("reschedule"):
            messages.warning(
                request,
                "This will return the status of the appointment to pending because the provider will have to review the timings again ",
            )
            change_appointment = Appointment.objects.get(id=request.POST.get("reschedule"))
            if change_appointment.status != "accepted":
                messages.error(request, "sorry you cannot reschedule a non accepted appointment ")
                return redirect("viewappointments")
            else :
                return redirect("reschedule", appointment_id=request.POST.get("reschedule"))
        if request.POST.get("cancel"):
            appointment = Appointment.objects.get(id=request.POST.get("cancel"))
            service = get_calendar_service(appointment.provider)
            service.events().delete(
                calendarId="primary", eventId=appointment.event_id
            ).execute()
            appointment.status = "cancelled"
            appointment.save()
            messages.success(request, "Cancelled successfully ")
            return redirect("viewappointments")
    return render(
        request, "customer/viewappointments.html", {"appointments": myappointments}
    )


@login_required(login_url="/login/")
def reschedule(request, appointment_id):
    change_appointment = Appointment.objects.get(id=appointment_id)
    if request.method == "POST":
        if request.POST.get("checkschedule"):
            request.session["mode"] = "reschedule"
            print(f"DEBUG : THE CURRENT MODE IS {request.session.get("mode")}")
            print(f"appointment ID currently is {appointment_id}")
            messages.info(
                request,
                "Here is the providers schedule , please take note and choose a slot ",
            )
            return redirect(
                "schedule", providerID=change_appointment.provider.providerprofile.id
            )
    return render(request, "customer/reschedule.html")
