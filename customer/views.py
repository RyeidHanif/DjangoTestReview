from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Permission, User
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.timezone import (get_current_timezone, localdate, localtime,
                                   make_aware)

from main.models import Appointment, ProviderProfile , NotificationPreferences
from main.utils import get_calendar_service, cancellation

from .utils import (EmailRescheduledAppointment, check_appointment_exists,
                    create_calendar_appointment, get_available_slots , EmailPendingAppointment,calculate_total_price, create_and_save_appointment, create_google_calendar_event,reschedule_google_event  , change_and_save_appointment)

from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
# Create your views here.
from .forms import AppointmentRecurrenceForm
from django.contrib.auth import logout
from django.views import View



# @login_required(login_url="/login/")
# def customerdashboard(request):
#     if request.method == "POST":
#         if request.POST.get("viewproviders"):
#             return redirect("viewproviders")
#         if request.POST.get("viewappointments"):
#             return redirect("viewappointments")
#         if request.POST.get("myprofile"):
#             return redirect("userprofile")
#         if request.POST.get("bookinghistory"):
#             return redirect("bookinghistory")
#     return render(request, "customer/customerdashboard.html")

class CustomerDashboard(View , LoginRequiredMixin):
    login_url = "/login/"
    def get(self, request , *args , **kwargs):
        return render(request, "customer/customerdashboard.html")
    
    def post(self, request , *args , **kwargs):
        if request.POST.get("viewproviders"):
            return redirect("viewproviders")
        if request.POST.get("viewappointments"):
            return redirect("viewappointments")
        if request.POST.get("myprofile"):
            return redirect("userprofile")
        if request.POST.get("bookinghistory"):
            return redirect("bookinghistory")
        else :
            return self.get(request)
customerdashboard = CustomerDashboard.as_view()



# @login_required(login_url="/login/")
# def viewproviders(request):
#     query = request.GET.get('q')
#     if query :
#         providers = ProviderProfile.objects.filter(user__username__icontains= query).exclude(user=request.user)
#     else:

#         providers = ProviderProfile.objects.exclude(user=request.user)

#     categories = ["doctor", "consultant", "therapist", "counsellor"]
#     if request.method == "POST":
#         messages.info(
#             request, "You are being redirected to the service providers schedule"
#         )
#         return redirect("schedule", providerID=request.POST.get("bookappointment"))

#     return render(
#         request,
#         "customer/viewproviders.html",
#         {"providers": providers, "categories": categories},
#     )


class ViewProviders(ListView , LoginRequiredMixin):
    model = ProviderProfile
    template_name= "customer/viewproviders.html"
    context_object_name = "providers"

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query :
            return  ProviderProfile.objects.filter(user__username__icontains= query).exclude(user=self.request.user)
        else:
            return ProviderProfile.objects.exclude(user=self.request.user)
        

    def post(self , request , *args , **kwargs):
        messages.info(
            request, "You are being redirected to the service providers schedule"
        )
        return redirect("schedule", providerID=request.POST.get("bookappointment"))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) # first get the context then add stuff to it  to pass to the template 
        context['categories'] = ["doctor", "consultant", "therapist", "counsellor"]
        return context

viewproviders = ViewProviders.as_view()
        






# @login_required(login_url="/login/")
# def schedule(request, providerID):

#     provider_profile = ProviderProfile.objects.get(id=providerID)
#     provider = provider_profile.user
#     slot_range = 1

#     if request.method == "POST":
#         if request.POST.get("week"):
#             slot_range = 7
#         elif request.POST.get("day"):
#             slot_range = 1
#         elif request.POST.get("slot_range"):
#             slot_range = int(request.POST.get("slot_range"))
        

#         available_slots = get_available_slots(provider, slot_range)


#         if request.POST.get("addappointment"):
#             index = int(request.POST.get("addappointment"))
#             timeslot = available_slots[index]
#             request.session["timeslot_tuple"] = (
#                 timeslot[0].isoformat(),
#                 timeslot[1].isoformat(),
#             )
            
#             return redirect("addappointment", providerUserID=provider.id)

#     else:
#         available_slots = get_available_slots(provider, slot_range)

#     return render(
#         request,
#         "customer/schedule.html",
#         {
#             "available_slots": available_slots,
#             "provider": provider,
#             "slot_range": slot_range,
#         },
#     )


class Schedule(View , LoginRequiredMixin):
    login_url = "/login/"

    def dispatch(self, request, *args , **kwargs):
        self.provider_profile = ProviderProfile.objects.get(id=kwargs['providerID'])
        self.provider = self.provider_profile.user
        self.slot_range = 1 
        return super().dispatch(request , *args , **kwargs)
    

    def get(self , request , *args , **kwargs):
        self.available_slots = get_available_slots(self.provider , self.slot_range)
        return self.render_schedule(self.available_slots)
    

    def post(self , request , *args , **kwargs):
        if request.POST.get("week"):
            self.slot_range = 7
        elif request.POST.get("day"):
            self.slot_range = 1 
        elif request.POST.get("slot_range"): # hidden input 
            self.slot_range = int(request.POST.get("slot_range"))
        
        self.available_slots = get_available_slots(self.provider , self.slot_range)

        if request.POST.get("addappointment"):
            index = int(request.POST.get("addappointment"))
            self.timeslot = self.available_slots[index]
            request.session["timeslot_tuple"] = (
                self.timeslot[0].isoformat() ,
                self.timeslot[1].isoformat(),
            )

            return redirect("addappointment", providerUserID = self.provider.id)
        return self.render_schedule(self.available_slots)
    
    def render_schedule(self ,  *args , **kwargs):
        return render(self.request , "customer/schedule.html",{
            "available_slots": self.available_slots,
            "provider": self.provider , 
            "slot_range": self.slot_range,

        })

schedule = Schedule.as_view()










# @login_required(login_url="/login/")
# def addappointment(request, providerUserID):

#     mode = request.session.get("mode", "normal")
#     print(f"DEBUG : THE CURRENT MODE IS {mode}")
#     timeslot = request.session.get("timeslot_tuple", [])

#     provider_user = User.objects.get(id=providerUserID)
#     provider = ProviderProfile.objects.get(user=provider_user)
#     customer = request.user

#     start_datetime = datetime.fromisoformat(timeslot[0])
#     end_datetime = datetime.fromisoformat(timeslot[1])
#     total_price = calculate_total_price(provider)

#     print(f"DEBUG : THE CURRENT MODE IS {mode}")
#     if mode == "normal":
#         print(f"DEBUG : THE CURRENT MODE IS {mode}")
#         recurrence_form = AppointmentRecurrenceForm()

#         if not check_appointment_exists(customer, provider_user):
#             messages.warning(
#                 request,
#                 "You already have an appointment with this provider. Cancel that one first.",
#             )
#             return redirect("viewproviders")

#         if request.method == "POST":
#             print(f"DEBUG : THE CURRENT MODE IS {mode}")
#             recurrence_form = AppointmentRecurrenceForm(request.POST)
#             if request.POST.get("confirm"):
#                 if recurrence_form.is_valid():
#                     recurrence_frequency = recurrence_form.cleaned_data["recurrence"]
#                     until_date = recurrence_form.cleaned_data["until_date"]
#                 else:
#                     recurrence_frequency = None
#                     until_date = None

#                 special_requests = request.POST.get("special_requests", "")

#                 appointment = create_and_save_appointment(
#                     customer,
#                     provider_user,
#                     start_datetime,
#                     end_datetime,
#                     total_price,
#                     special_requests,
#                     recurrence_frequency,
#                     until_date,
#                 )

#                 # Removed google calendar API integration from here to prevent ghost appointments 
#                 if appointment.provider.notification_settings.preferences == "all":
#                     EmailPendingAppointment(
#                         request,
#                         customer,
#                         provider_user,
#                         start_datetime,
#                         end_datetime,
#                         provider_user.email,
#                         special_requests,
#                     )

#                 messages.success(request, "Appointment created successfully")
#                 return redirect("customerdashboard")

#             elif request.POST.get("cancel"):
#                 messages.info(request, "Appointment was not created")
#                 return redirect("customerdashboard")

#     elif mode == "reschedule":
#         print(f"DEBUG : THE CURRENT MODE IS {mode}")
#         appointment = Appointment.objects.filter(customer=customer, provider=provider_user).first()
#         recurrence_form = AppointmentRecurrenceForm(initial={
#             "recurrence": appointment.recurrence_frequency,
#             "until_date": appointment.recurrence_until
#         })
        
#         if not appointment:
#             messages.error(request, "No existing appointment found for rescheduling.")
#             return redirect("viewappointments")

#         if request.method == "POST":
#             print(f"DEBUG : THE CURRENT MODE IS {mode}")
#             recurrence_form = AppointmentRecurrenceForm(request.POST)
#             if recurrence_form.is_valid():
#                 if recurrence_form.is_valid():
#                     recurrence_frequency = recurrence_form.cleaned_data["recurrence"]
#                     until_date = recurrence_form.cleaned_data["until_date"]
#                 else:
#                     recurrence_frequency = appointment.recurrence_frequency
#                     until_date = appointment.recurrence_until

#             if request.POST.get("confirm"):
#                 old_start = appointment.date_start
#                 old_end = appointment.date_end

#                 appointment.date_start = start_datetime
#                 appointment.date_end = end_datetime
#                 appointment.status = "rescheduled"
#                 appointment.recurrence_frequency = recurrence_frequency
#                 appointment.recurrence_until = until_date
#                 appointment.special_requests = request.POST.get("special_requests", "")
#                 appointment.save()

                
#                 if appointment.provider.notification_settings.preferences == "all":

#                     EmailRescheduledAppointment(
#                         request,
#                         customer,
#                         provider_user,
#                         localtime(old_start),
#                         localtime(old_end),
#                         localtime(appointment.date_start),
#                         localtime(appointment.date_end),
#                         provider_user.email,
#                         appointment.special_requests,
#                     )

#                 request.session.pop("mode", None)
#                 messages.success(request, "Appointment rescheduled successfully")
#                 return redirect("viewappointments")

#             elif request.POST.get("cancel"):
#                 messages.info(request, "Reschedule cancelled")
#                 return redirect("viewappointments")

#     return render(
#         request,
#         "customer/addappointment.html",
#         {
#             "start": start_datetime,
#             "end": end_datetime,
#             "form": recurrence_form,
#             "mode": mode,
#             "appointment": appointment if mode == "reschedule" else None,
#         },
#     )





class AddAppointment(View , LoginRequiredMixin):
    def dispatch(self , request , *args , **kwargs):
        self.mode = request.session.get("mode", "normal")
        self.timeslot = request.session.get("timeslot_tuple", [])
        self.provider_user = User.objects.get(id=kwargs['providerUserID'])
        self.provider = ProviderProfile.objects.get(user=self.provider_user)
        self.customer = request.user
        self.start_datetime = datetime.fromisoformat(self.timeslot[0])
        self.end_datetime = datetime.fromisoformat(self.timeslot[1])
        self.total_price = calculate_total_price(self.provider)
        self.recurrence_form = AppointmentRecurrenceForm()
        self.appointment = None
        return super().dispatch(request, *args, **kwargs)

    def get(self, request ,*args , **kwargs):
        if self.mode == "normal":
            return self.handle_normal_get(request, *args , **kwargs)
        elif self.mode == "reschedule":
            return self.handle_reschedule_get(request , *args , **kwargs)

    def post(self, request , *args , **kwargs):
        if self.mode == "normal":
            return self.handle_normal_post(request , *args , **kwargs)
        elif self.mode == "reschedule":
            return self.handle_reschedule_post(request , *args , **kwargs)

    def handle_normal_get(self,request, *args , **kwargs):
        self.recurrence_form = AppointmentRecurrenceForm()
        if not check_appointment_exists(self.customer , self.provider_user):
            messages.warning(request," You already have an appointment with this provider , Cancel or complete thatone first")
            return redirect("viewproviders")

        return self.render_template(request)
        

    def handle_normal_post(self, request , *args , **kwargs):
        self.recurrence_form = AppointmentRecurrenceForm(request.POST)
        if request.POST.get("confirm"):
            recurrence_frequency = None
            until_date =None
            if self.recurrence_form.is_valid():
                recurrence_frequency = self.recurrence_form.cleaned_data["recurrence"]
                until_date = self.recurrence_form.cleaned_data["until_date"]
            
            self.special_requests =  request.POST.get("special_requests", " ")
            appointment = create_and_save_appointment(self.customer , self.provider_user , self.start_datetime , self.end_datetime , self.total_price , self.special_requests , recurrence_frequency , until_date)
            if appointment.provider.notification_settings.preferences == "all":
                  EmailPendingAppointment(
                        request,
                        self.customer,
                        self.provider_user,
                        self.start_datetime,
                        self.end_datetime,
                        self.provider_user.email,
                        self.special_requests,
                    )
            messages.success(request, " Appointment Created Succesfully ")
            return redirect("customerdashboard")
        elif request.POST.get("cancel"):
            messages.info(request,"Appointment Was NOT created")
            return redirect("customerdashboard")
        

    def handle_reschedule_get(self ,request, *args , **kwargs):
        self.appointment = Appointment.objects.filter(customer=self.customer, provider=self.provider_user).first()
        self.recurrence_form = AppointmentRecurrenceForm(initial={
            "recurrence": self.appointment.recurrence_frequency,
            "until_date": self.appointment.recurrence_until
        })
        if not self.appointment:
            messages.error(request, "No existing appointment found for recheduling ")
            return redirect("viewappointments")
        return self.render_template(request)
    

    def handle_reschedule_post(self , request , *args , **kwargs):
        self.recurrence_form = AppointmentRecurrenceForm(request.POST)
        if self.recurrence_form.is_valid():
            recurrence_frequency = self.recurrence_form.cleaned_data["recurrence"]
            until_date = self.recurrence_form.cleaned_data["until_date"]
        else :
            recurrence_frequency = self.appointment.recurrence_frequency
            until_date = self.appointment.recurrence_until
        
        if request.POST.get("confirm"):
            self.appointment = Appointment.objects.filter(customer=self.customer, provider=self.provider_user).first()
            self.appointment = change_and_save_appointment(request , self.appointment , recurrence_frequency , until_date, self.start_datetime , self.end_datetime)
            request.session.pop("mode", None)
            if self.appointment :
                messages.success(request ," appointment reschedule successfully ")
                return redirect("viewappointments")
            else :
                messages.error(request, "invalid stuff added")
                return redirect("viewappointments")
        if request.POST.get("cancel"):
            messages.info(request, "reschedule ancelled")
            return redirect("viewappoinments")

            

    def render_template(self , request , *args , **kwargs):
        return render(request, "customer/addappointment.html", {
            "start": self.start_datetime,
            "end": self.end_datetime ,
            "form": self.recurrence_form,
            "mode":self.mode ,
            "appointment": self.appointment if self.mode=="reschedule" else None 

        })
    
addappointment = AddAppointment.as_view()



# @login_required(login_url="/login/")
# def viewappointments(request):
#     query =  request.GET.get("q")
#     if query :
#         myappointments = (
#         Appointment.objects.filter(customer=request.user, provider__username__icontains=query)
#         .order_by("-date_added")
#         .all()
#         .exclude(status="rejected")
#         .exclude(status="cancelled").exclude(status="completed")
#     )
#     else:

#         myappointments = (
#             Appointment.objects.filter(customer=request.user)
#             .order_by("-date_added")
#             .all()
#             .exclude(status="rejected")
#             .exclude(status="cancelled").exclude(status="completed")
#         )
#     if request.method == "POST":
#         if request.POST.get("reschedule"):
#             messages.warning(
#                 request,
#                 "This will change the status to Rescheduled but the event for now will remain in the calendar  because the provider will have to review the timings again ",
#             )
#             change_appointment = Appointment.objects.get(
#                 id=request.POST.get("reschedule")
#             )
#             if change_appointment.status != "accepted":
#                 messages.error(
#                     request, "sorry you cannot reschedule a non accepted appointment "
#                 )
#                 return redirect("viewappointments")
#             else:
#                 return redirect(
#                     "reschedule", appointment_id=request.POST.get("reschedule")
#                 )
#         if request.POST.get("cancel"):
#             appointment = Appointment.objects.get(id=request.POST.get("cancel"))
#             count_cancel = cancellation(request.user , appointment)
#             if appointment.status == "accepted":
#                 service = get_calendar_service(appointment.provider)
#                 service.events().delete(calendarId="primary" , eventId = appointment.event_id).execute()
#             appointment.status = "cancelled"
#             appointment.save()
#             if count_cancel >= 3 :
#                 request.user.is_active = False
#                 request.user.save()
#                 logout(request)
#                 messages.warning(request,"You have cancelled too many appointments in a shot span , your account has been deactivated ")
#                 return redirect("home")
#             else:
#                 messages.success(request, "Cancelled successfully ")
#                 return redirect("viewappointments")
#     return render(
#         request, "customer/viewappointments.html", {"appointments": myappointments}
#     )


class ViewAppointments(View , LoginRequiredMixin):
    login_url = "/login/"

    def get(self , request , *args , **kwargs):
        
        self.myappointments = self.get_query(request, *args, **kwargs)
        return render(request , "customer/viewappointments.html", {"appointments": self.myappointments})

    def post(self, request , *args , **kwargs):
        if request.POST.get("reschedule"):
            self.appointmentID = request.POST.get("reschedule")
            return self.reschedule(request , *args , **kwargs)
        elif request.POST.get("cancel"):
            self.appointmentID = request.POST.get("cancel")
            return self.cancel(request, *args , **kwargs)


    def get_query(self , request , *args , **kwargs):
        query = request.GET.get("q")
        if query :
            return Appointment.objects.filter(customer=request.user, provider__username__icontains=query).order_by("-date_added").all().exclude(status="rejected").exclude(status="cancelled").exclude(status="completed")
        else:

            return Appointment.objects.filter(customer=request.user).order_by("-date_added").all().exclude(status="rejected").exclude(status="cancelled").exclude(status="completed")
        
    
    def reschedule(self, request, *args , **kwargs):
        messages.warning(
                request,
                "This will change the status to Rescheduled but the event for now will remain in the calendar  because the provider will have to review the timings again ",
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
                    "reschedule", appointment_id=self.appointmentID
                )
        
    def cancel(self , request, *args , **kwargs):
        appointment = Appointment.objects.get(id=self.appointmentID)
        count_cancel = cancellation(request.user , appointment)
        if appointment.status == "accepted":
            service = get_calendar_service(appointment.provider)
            service.events().delete(calendarId="primary" , eventId = appointment.event_id).execute()
        appointment.status = "cancelled"
        appointment.save()
        if count_cancel >= 3 :
            request.user.is_active = False
            request.user.save()
            logout(request)
            messages.warning(request,"You have cancelled too many appointments in a shot span , your account has been deactivated ")
            return redirect("home")
        else:
            messages.success(request, "Cancelled successfully ")
            return redirect("viewappointments")

viewappointments = ViewAppointments.as_view()
    




# very simple . left this as FBV . doesnt fit in any generic CBVs and View CBV will just have more boilerplate
@login_required(login_url="/login/")
def reschedule(request, appointment_id):
    change_appointment = Appointment.objects.get(id=appointment_id)
    if request.method == "POST":
        if request.POST.get("checkschedule"):
            request.session["mode"] = "reschedule"
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