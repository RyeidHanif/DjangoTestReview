from django.shortcuts import render , redirect
from django.contrib.auth.decorators import login_required
from main.models import ProviderProfile,Appointment
from django.contrib.auth.models import User
from django.contrib import messages
from datetime import datetime , time , timedelta
from django.utils.timezone import get_current_timezone , make_aware , localtime , localdate
from main.utils import get_calendar_service
from django.http import HttpResponse
from .utils import get_available_slots, create_calendar_appointment, check_appointment_exists
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import Permission
# Create your views here.

@login_required(login_url="/login/")
def customerdashboard(request):
    if request.method == "POST":
        if request.POST.get("viewproviders"):
            return redirect("viewproviders")
        if request.POST.get("viewappointments"):
            return redirect("viewappointments")
    return render(request , "customer/customerdashboard.html")





@login_required(login_url= "/login/")
def viewproviders(request):
    providers = ProviderProfile.objects.exclude(user=request.user)
    categories = ["doctor" , "consultant", "therapist", "counsellor"]
    if request.method == "POST":
        print(f"The current provider  at the end of viewproviders function is {ProviderProfile.objects.get(id=request.POST.get("bookappointment")).user.username}")
        messages.info(request, "You are being redirected to the service providers schedule")
        return redirect("schedule", providerID = request.POST.get("bookappointment"))
    return render(request, "customer/viewproviders.html", {"providers": providers , "categories" : categories})


@login_required(login_url="/login/")
def schedule(request, providerID):
    print(f"The Current provider : start of schedule function is {ProviderProfile.objects.get(id=providerID).user.username}")
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
            request.session['timeslot_tuple'] = (timeslot[0].isoformat(), timeslot[1].isoformat())
            print(f"The current provider , at the end of scheudle functions is {User.objects.get(id=provider.id).username} ")
            return redirect("addappointment", providerUserID=provider.id)

    else:
        available_slots = get_available_slots(provider, slot_range)

    return render(request, "customer/schedule.html", {
        "available_slots": available_slots,
        "provider": provider,
        "slot_range": slot_range
    })



@login_required(login_url="/login/")
def addappointment(request , providerUserID):
    timeslot = request.session.get('timeslot_tuple', [])
    provider_user = User.objects.get(id=providerUserID)
    provider = ProviderProfile.objects.get(user=provider_user)
    start_datetime = datetime.fromisoformat(timeslot[0])
    end_datetime = datetime.fromisoformat(timeslot[1])
    print(f"The current provider is {provider_user.username}")
    customer= request.user
    if not check_appointment_exists(customer , provider_user):
        messages.warning(request , "You already have an appointment with this provider . please cancel that one to create a new one ")
        return redirect("viewproviders")

    if request.method == "POST":
        if request.POST.get("confirm"):
            newappointment = Appointment(provider=provider_user , customer = request.user , date_start = start_datetime , date_end = end_datetime)
    
            summary = f"Appointment with {newappointment.customer.username } "
            attendee_email = newappointment.customer.email
            event = create_calendar_appointment(timeslot[0], timeslot[1],summary, attendee_email)
            service = get_calendar_service(provider_user)
            event = service.events().insert(calendarId='primary', body=event,sendUpdates = 'all' ).execute()
            event_id = event['id']
            newappointment.event_id = event_id 
            newappointment.save()
        
            messages.success(request, "Event created successfully ")
            return redirect("customerdashboard")
        
        elif request.POST.get("cancel"):
            cancel_appointment = Appointment.objects.filter(provider=provider_user , customer = request.user , date_start = start_datetime , date_end = end_datetime ).first()
            service = get_calendar_service(cancel_appointment.provider)
            service.events().delete(calendarId = 'primary', eventId = cancel_appointment.event_id).execute()
            cancel_appointment.delete()
    
            messages.success(request, "Appointment cancelled successfully ")
            return redirect("customerdashboard")
    
    return render(request, "customer/addappointment.html", {"start": start_datetime, "end": end_datetime} )




@login_required(login_url="/login/")
def viewappointments(request):
    myappointments = Appointment.objects.filter(customer=request.user).all().exclude(status = "rejected")
    if request.method == "POST":
        if request.POST.get("reschedule"):
            messages.warning(request , "This will return the status of the appointment to pending because the provider will have to review the timings again ")
            return redirect("reschedule" , appointmentid = request.POST.get("reschedule"))
        if request.POST.get("cancel"):
            appointment = Appointment.objects.get(id=request.POST.get("cancel"))
            service = get_calendar_service(appointment.provider)
            service.events().delete(calendarId = 'primary', eventId = appointment.event_id).execute()
            appointment.delete()
            messages.success(request, "Cancelled successfully ")
            return redirect("viewappointments")
    return render(request , "customer/viewappointments.html" , {"appointments": myappointments })