from django.shortcuts import render , redirect
from django.contrib.auth.decorators import login_required
from main.models import ProviderProfile
from django.contrib.auth.models import User
from django.contrib import messages
from datetime import datetime , time , timedelta
from django.utils.timezone import get_current_timezone , make_aware , localtime , localdate
from main.utils import get_calendar_service
from django.http import HttpResponse
from .utils import get_available_slots
# Create your views here.

@login_required(login_url="/login/")
def customerdashboard(request):

    if hasattr(request.user ,'providerprofile'):
        display = "Go to provider Dashboard"
        if request.method == "POST":
            if request.POST.get("providerside"):
                return redirect("providerdashboard")
        
    else :
        display = "Become a Service Provider "
        if request.method == "POST":
            if request.POST.get("providerside"):
                return redirect("profile_creation")
    return render(request , "customer/customerdashboard.html", {"user": request.user , "display": display})






@login_required(login_url= "/login/")
def viewproviders(request):
    providers = ProviderProfile.objects.all()
    categories = ["doctor" , "consultant", "therapist", "counsellor"]
    if request.method == "POST":
        messages.info(request, "You are being redirected to the service providers schedule")
        return redirect("schedule", providerID = request.POST.get("bookappointment"))
    return render(request, "customer/viewproviders.html", {"providers": providers , "categories" : categories})


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

        if request.POST.get("addappointment"):
            index = int(request.POST.get("addappointment"))
            timeslot = available_slots[index]
            request.session['timeslot_tuple'] = (timeslot[0].isoformat(), timeslot[1].isoformat())
            return redirect("addappointment", providerID=provider.id)

    else:
        available_slots = get_available_slots(provider, slot_range)

    return render(request, "customer/schedule.html", {
        "available_slots": available_slots,
        "provider": provider,
        "slot_range": slot_range
    })


@login_required(login_url="/login/")
def addappointment(request , providerID):
    timeslot = request.session.get('timeslot_tuple', [])
    
    return render(request, "customer/addappointment.html", {"timeslot_start": timeslot[0], "timeslot_end": timeslot[1]} )


