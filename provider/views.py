from datetime import datetime, timedelta
from django.db.models  import Q

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.timezone import (activate, get_current_timezone, localdate,
                                   localtime, make_aware, now)

from main.models import Appointment, ProviderProfile ,NotificationPreferences
from main.utils import get_calendar_service

from .forms import AvailabilityForm , SendNoteForm
from .utils import (EmailCancelledAppointment, EmailConfirmedAppointment,
                    EmailDeclinedAppointment, create_google_calendar_event , reschedule_google_event , SendEmailRescheduleAccepted ,EmailRescheduleDeclined)
from django.utils.timezone import localtime
from datetime import datetime, time

# Create your views here.
from django.shortcuts import redirect, render
from main.utils import cancellation
from django.contrib.auth import logout


@login_required(login_url="/login/")
def provider_dashboard(request):
    if request.method == "POST":
        if request.POST.get("myprofile"):
            return redirect("user_profile")
        if request.POST.get("viewanalytics"):
            return redirect("viewanalytics")
        if request.POST.get("viewmyappointments"):
            return redirect("view_my_appointments")
        if request.POST.get("viewpendingappointments"):
            return redirect("view_pending_appointments")
        if request.POST.get("myavailability"):
            return redirect("myavailability")

    return render(request, "provider/provider_dashboard.html")


@login_required(login_url="/login/")
def view_my_appointments(request):
    query = request.GET.get("q")
    if query:
        my_appointments = Appointment.objects.filter(
        provider=request.user, status="accepted", customer__username__icontains=query,
        ).order_by("-date_added")
    else : 
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
            if customer.notification_settings.preferences == "all":
                EmailCancelledAppointment(request, customer, provider, to_email)
            count_cancel = cancellation(request , request.user , cancel_appointment)
            if count_cancel >= 3 :
                request.user.is_active = False
                request.user.save()
                logout(request)
                messages.warning(request , "you cancelled too many apointments after deadline in a short span of time ")
                return redirect("home")
            else:
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

    query= request.GET.get("q")
    if query :
        my_appointments = Appointment.objects.filter(status__in=["pending", "rescheduled"] , provider = request.user , customer__username__icontains=query)
    else :
        my_appointments = Appointment.objects.filter(status__in=["pending", "rescheduled"] , provider = request.user)

    
    if request.method == "POST":
        if request.POST.get("reject"):
            appointment = Appointment.objects.get(id=request.POST.get("reject"))
            service = get_calendar_service(request.user)
            service.events().delete(calendarId="primary", eventId=appointment.event_id).execute()
            if appointment.status == "pending":
                appointment.status = "rejected"
                if appointment.customer.notification_settings.preferences == "all":
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
            elif appointment.status == "rescheduled":
                appointment.status ="cancelled"
                appointment.save()
                messages.info(request , "reschedule rejected successfully ")
                if appointment.customer.notification_settings.preferences == "all":
                    EmailRescheduleDeclined(request , appointment.customer,  appointment.provider , appointment.date_start , appointment.date_end , appointment.customer.email)
        if request.POST.get("accept") :
            appointment = Appointment.objects.get(id=request.POST.get("accept"))
            if appointment.status == "pending":
                appointment.status = "accepted"
                #add the rest here 
                summary = f"Appointment with {appointment.customer.username}"
                service = get_calendar_service(appointment.provider)
        
                timeslot = (localtime(appointment.date_start).isoformat() , localtime(appointment.date_end).isoformat())
                event = create_google_calendar_event(
                    service,
                    timeslot,
                    summary,
                    appointment.customer.email,
                    appointment.recurrence_frequency,
                    appointment.recurrence_until,
                    appointment,
                )

                appointment.event_id = event["id"]
                appointment.save()
                if appointment.customer.notification_settings.preferences == "all":
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
            elif appointment.status == "rescheduled":
                appointment.status = "accepted"
                service = get_calendar_service(request.user)
                reschedule_google_event(
                    service, appointment.event_id, localtime(appointment.date_start).isoformat(), localtime(appointment.date_end).isoformat() , appointment.recurrence_frequency , appointment.recurrence_until
                )
                SendEmailRescheduleAccepted(request, appointment.customer , appointment.provider , appointment.date_start ,appointment.date_end, appointment.customer.email)
                appointment.save()




    return render(
        request,
        "provider/view_pending_appointments.html",
        {"appointments": my_appointments},
    )





def my_availability(request):



    if request.method == "POST":
        form = AvailabilityForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data["start_date"]
            end_date = form.cleaned_data["end_date"]
            start_time = form.cleaned_data["start_time"]
            end_time = form.cleaned_data["end_time"]
            cause = form.cleaned_data["cause"]
            start_datetime = make_aware(
                datetime.combine(start_date, start_time), timezone=get_current_timezone()
            )
            end_datetime = make_aware(datetime.combine(end_date, end_time), timezone=get_current_timezone())
            start_datetime_iso = start_datetime.isoformat()
            end_datetime_iso = end_datetime.isoformat()
            service = get_calendar_service(request.user)
            # this is a test event , to see if calendar integration is woking properly
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
            return redirect("my_availability")

    else:
        form = AvailabilityForm()

    return render(request, "provider/my_availability.html", {"form": form})



@login_required(login_url="/login/")
def view_analytics(request):
    revenue = 0
    myappointments = Appointment.objects.filter(provider=request.user)
    total_statuses = 0
    percentage_statuses_dict = {}
    statuses = {"pending": 0,
                "accepted":0 ,
                "rejected": 0,
                "cancelled": 0,
                "completed": 0,
                "rescheduled":0,
                }
    customers = []
    for appointment in myappointments :
        statuses[appointment.status] +=1
        total_statuses +=1
        customers.append(appointment.customer.username)
        if appointment.status in ["accepted" , "completed"]:
            revenue += appointment.total_price
    
    admin_cut = 0.05 * revenue
    for key,value in statuses.items():
            if total_statuses != 0 :
                percentage = (value/total_statuses)*100
            else :
                percentage= 0
            percentage_statuses_dict[key] = percentage



    

    
    return render(request , "provider/view_analytics.html" , {"customers": customers , "myappointments": myappointments , "statuses": statuses , "revenue": revenue,  "admin_cut": admin_cut, "percentage_statuses_dict":percentage_statuses_dict} )
        



        
