from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Permission, User
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.timezone import (get_current_timezone, localdate, localtime,
                                   make_aware)

from main.models import Appointment, ProviderProfile
from main.utils import get_calendar_service

from .utils import (EmailRescheduledAppointment, check_appointment_exists,
                    create_calendar_appointment, get_available_slots , EmailPendingAppointment,calculate_total_price, create_and_save_appointment, create_google_calendar_event,reschedule_google_event )

from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
# Create your views here.
from .forms import AppointmentRecurrenceForm


@login_required(login_url="/login/")
def customerdashboard(request):
    if request.method == "POST":
        if request.POST.get("viewproviders"):
            return redirect("viewproviders")
        if request.POST.get("viewappointments"):
            return redirect("viewappointments")
        if request.POST.get("myprofile"):
            return redirect("userprofile")
        if request.POST.get("bookinghistory"):
            return redirect("bookinghistory")
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
    timeslot = request.session.get("timeslot_tuple", [])

    provider_user = User.objects.get(id=providerUserID)
    provider = ProviderProfile.objects.get(user=provider_user)
    customer = request.user

    start_datetime = datetime.fromisoformat(timeslot[0])
    end_datetime = datetime.fromisoformat(timeslot[1])
    total_price = calculate_total_price(provider)

    recurrence_form = AppointmentRecurrenceForm(request.POST or None)

    if mode == "normal":
        if not check_appointment_exists(customer, provider_user):
            messages.warning(
                request,
                "You already have an appointment with this provider. Cancel that one first.",
            )
            return redirect("viewproviders")

        if request.method == "POST":
            if request.POST.get("confirm"):
                if recurrence_form.is_valid():
                    recurrence_frequency = recurrence_form.cleaned_data["recurrence"]
                    until_date = recurrence_form.cleaned_data["until_date"]
                else:
                    recurrence_frequency = None
                    until_date = None

                special_requests = request.POST.get("special_requests", "")

                appointment = create_and_save_appointment(
                    customer,
                    provider_user,
                    start_datetime,
                    end_datetime,
                    total_price,
                    special_requests,
                    recurrence_frequency,
                    until_date,
                )

                summary = f"Appointment with {customer.username}"
                service = get_calendar_service(provider_user)
                event = create_google_calendar_event(
                    service,
                    timeslot,
                    summary,
                    customer.email,
                    recurrence_frequency,
                    until_date,
                )

                appointment.event_id = event["id"]
                appointment.save()

                EmailPendingAppointment(
                    request,
                    customer,
                    provider_user,
                    start_datetime,
                    end_datetime,
                    provider_user.email,
                )

                messages.success(request, "Appointment created successfully")
                return redirect("customerdashboard")

            elif request.POST.get("cancel"):
                messages.info(request, "Appointment was not created")
                return redirect("customerdashboard")

    elif mode == "reschedule":
        appointment = Appointment.objects.filter(customer=customer, provider=provider_user).first()
        if not appointment:
            messages.error(request, "No existing appointment found for rescheduling.")
            return redirect("viewappointments")

        if request.method == "POST":
            if request.POST.get("confirm"):
                old_start = appointment.date_start
                old_end = appointment.date_end

                appointment.date_start = start_datetime
                appointment.date_end = end_datetime
                appointment.save()

                service = get_calendar_service(provider_user)
                reschedule_google_event(
                    service, appointment.event_id, timeslot[0], timeslot[1]
                )

                EmailRescheduledAppointment(
                    request,
                    customer,
                    provider_user,
                    localtime(old_start),
                    localtime(old_end),
                    localtime(appointment.date_start),
                    localtime(appointment.date_end),
                    provider_user.email,
                )

                request.session.pop("mode", None)
                messages.success(request, "Appointment rescheduled successfully")
                return redirect("viewappointments")

            elif request.POST.get("cancel"):
                messages.info(request, "Reschedule cancelled")
                return redirect("viewappointments")

    return render(
        request,
        "customer/addappointment.html",
        {
            "start": start_datetime,
            "end": end_datetime,
            "form": recurrence_form,
        },
    )




@login_required(login_url="/login/")
def viewappointments(request):
    myappointments = (
        Appointment.objects.filter(customer=request.user)
        .order_by("-date_added")
        .all()
        .exclude(status="rejected")
        .exclude(status="cancelled").exclude(status="completed")
    )
    if request.method == "POST":
        if request.POST.get("reschedule"):
            messages.warning(
                request,
                "This will return the status of the appointment to pending because the provider will have to review the timings again ",
            )
            change_appointment = Appointment.objects.get(
                id=request.POST.get("reschedule")
            )
            if change_appointment.status != "accepted":
                messages.error(
                    request, "sorry you cannot reschedule a non accepted appointment "
                )
                return redirect("viewappointments")
            else:
                return redirect(
                    "reschedule", appointment_id=request.POST.get("reschedule")
                )
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




class BookingHistoryView(LoginRequiredMixin , ListView):
    model = Appointment
    template_name = "customer/bookinghistory.html"
    context_object_name = "appointments"
    ordering = ["-date_added"]
    

    def get_queryset(self):

        return Appointment.objects.filter(customer=self.request.user).order_by("-date_added")
    

bookinghistory = BookingHistoryView.as_view()