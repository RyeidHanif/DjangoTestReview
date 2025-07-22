from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.timezone import (get_current_timezone, localdate, localtime,
                                   make_aware)

from main.models import ProviderProfile
from main.utils import get_calendar_service

from .utils import get_available_slots

# Create your views here.


@login_required(login_url="/login/")
def customer_dashboard(request):

    if hasattr(request.user, "providerprofile"):
        display = "Go to provider Dashboard"
        if request.method == "POST":
            if request.POST.get("provider_side"):
                return redirect("provider_dashboard")

    else:
        display = "Become a Service Provider "
        if request.method == "POST":
            if request.POST.get("providerside"):
                return redirect("profile_creation")
    return render(
        request,
        "customer/customer_dashboard.html",
        {"user": request.user, "display": display},
    )


@login_required(login_url="/login/")
def view_providers(request):
    providers = ProviderProfile.objects.all()
    categories = ["doctor", "consultant", "therapist", "counsellor"]
    if request.method == "POST":
        messages.info(
            request, "You are being redirected to the service providers schedule"
        )
        return redirect("schedule", providerID=request.POST.get("book_appointment"))
    return render(
        request,
        "customer/view_providers.html",
        {"providers": providers, "categories": categories},
    )


@login_required(login_url="/login/")
def schedule(request, providerID):
    provider = User.objects.get(id=providerID)
    slot_range = 1

    if request.method == "POST":
        if request.POST.get("week"):
            slot_range = 7
        elif request.POST.get("day"):
            slot_range = 1
        elif request.POST.get("slot_range"):
            slot_range = int(request.POST.get("slot_range"))

        available_slots = get_available_slots(provider, slot_range)

        if request.POST.get("add_appointment"):
            index = int(request.POST.get("add_appointment"))
            timeslot = available_slots[index]
            request.session["timeslot_tuple"] = (
                timeslot[0].isoformat(),
                timeslot[1].isoformat(),
            )
            return redirect("add_appointment", providerID=provider.id)

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
def add_appointment(request, providerID):
    timeslot = request.session.get("timeslot_tuple", [])

    return render(
        request,
        "customer/add_appointment.html",
        {"timeslot_start": timeslot[0], "timeslot_end": timeslot[1]},
    )
