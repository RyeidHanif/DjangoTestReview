from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Permission, User
from django.core.cache import cache
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.timezone import (get_current_timezone, localdate, localtime,
                                   make_aware)
from django.views import View
from django.views.decorators.cache import cache_page
from django.views.generic import ListView

from main.models import Appointment, NotificationPreferences, ProviderProfile
from main.utils import cancellation, get_calendar_service

# Create your views here.
from .forms import AppointmentRecurrenceForm
from .utils import (EmailPendingAppointment, EmailRescheduledAppointment,
                    calculate_total_price, change_and_save_appointment,
                    check_appointment_exists, create_and_save_appointment,
                    create_calendar_appointment, create_google_calendar_event,
                    get_available_slots, reschedule_google_event)


class CustomerDashboard(View, LoginRequiredMixin):
    login_url = "/login/"

    def get(self, request, *args, **kwargs):
        return render(request, "customer/customerdashboard.html")

    def post(self, request, *args, **kwargs):
        if request.POST.get("viewproviders"):
            return redirect("viewproviders")
        if request.POST.get("viewappointments"):
            return redirect("viewappointments")
        if request.POST.get("myprofile"):
            return redirect("userprofile")
        if request.POST.get("bookinghistory"):
            return redirect("bookinghistory")
        else:
            return self.get(request)


customerdashboard = CustomerDashboard.as_view()


class ViewProviders(ListView, LoginRequiredMixin):
    model = ProviderProfile
    template_name = "customer/viewproviders.html"
    context_object_name = "providers"

    def get_queryset(self):
        query = self.request.GET.get("q")
        key = f"view_providers_for_user_{self.request.user.id}_with_{query}"
        provider_list = cache.get(key)
        if provider_list:
            return provider_list
        else:

            if query:
                provider_list = ProviderProfile.objects.filter(
                    user__username__icontains=query
                ).exclude(user=self.request.user)
            else:
                provider_list = ProviderProfile.objects.exclude(user=self.request.user)
            cache.set(key, list(provider_list), timeout=60 * 5)
            return provider_list

    def post(self, request, *args, **kwargs):
        messages.info(
            request, "You are being redirected to the service providers schedule"
        )
        return redirect("schedule", providerID=request.POST.get("bookappointment"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(
            **kwargs
        )  # first get the context then add stuff to it  to pass to the template
        context["categories"] = ["doctor", "consultant", "therapist", "counsellor"]
        return context


viewproviders = ViewProviders.as_view()


class Schedule(View, LoginRequiredMixin):
    login_url = "/login/"

    def dispatch(self, request, *args, **kwargs):

        self.provider_profile = ProviderProfile.objects.select_related("user").get(
            id=kwargs["providerID"]
        )
        self.provider = self.provider_profile.user
        self.slot_range = 1
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.available_slots = get_available_slots(self.provider, self.slot_range)
        return self.render_schedule(self.available_slots)

    def post(self, request, *args, **kwargs):
        if request.POST.get("week"):
            self.slot_range = 7
        elif request.POST.get("day"):
            self.slot_range = 1
        elif request.POST.get("slot_range"):  # hidden input
            self.slot_range = int(request.POST.get("slot_range"))

        self.available_slots = get_available_slots(self.provider, self.slot_range)

        if request.POST.get("addappointment"):
            index = int(request.POST.get("addappointment"))
            self.timeslot = self.available_slots[index]
            request.session["timeslot_tuple"] = (
                self.timeslot[0].isoformat(),
                self.timeslot[1].isoformat(),
            )

            return redirect("addappointment", providerUserID=self.provider.id)
        return self.render_schedule(self.available_slots)

    def render_schedule(self, *args, **kwargs):
        return render(
            self.request,
            "customer/schedule.html",
            {
                "available_slots": self.available_slots,
                "provider": self.provider,
                "slot_range": self.slot_range,
            },
        )


schedule = Schedule.as_view()


class AddAppointment(View, LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        self.mode = request.session.get("mode", "normal")
        self.timeslot = request.session.get("timeslot_tuple", [])
        self.provider_user = User.objects.get(id=kwargs["providerUserID"])
        self.provider = ProviderProfile.objects.get(user=self.provider_user)
        self.customer = request.user
        self.start_datetime = datetime.fromisoformat(self.timeslot[0])
        self.end_datetime = datetime.fromisoformat(self.timeslot[1])
        self.total_price = calculate_total_price(self.provider)
        self.recurrence_form = AppointmentRecurrenceForm()
        self.appointment = None
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if self.mode == "normal":
            return self.handle_normal_get(request, *args, **kwargs)
        elif self.mode == "reschedule":
            return self.handle_reschedule_get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if self.mode == "normal":
            return self.handle_normal_post(request, *args, **kwargs)
        elif self.mode == "reschedule":
            return self.handle_reschedule_post(request, *args, **kwargs)

    def handle_normal_get(self, request, *args, **kwargs):
        self.recurrence_form = AppointmentRecurrenceForm()
        if not check_appointment_exists(self.customer, self.provider_user):
            messages.warning(
                request,
                " You already have an appointment with this provider , Cancel or complete thatone first",
            )
            return redirect("viewproviders")

        return self.render_template(request)

    def handle_normal_post(self, request, *args, **kwargs):
        self.recurrence_form = AppointmentRecurrenceForm(request.POST)
        if request.POST.get("confirm"):
            recurrence_frequency = None
            until_date = None
            if self.recurrence_form.is_valid():
                recurrence_frequency = self.recurrence_form.cleaned_data["recurrence"]
                until_date = self.recurrence_form.cleaned_data["until_date"]

            self.special_requests = request.POST.get("special_requests", " ")
            appointment = create_and_save_appointment(
                self.customer,
                self.provider_user,
                self.start_datetime,
                self.end_datetime,
                self.total_price,
                self.special_requests,
                recurrence_frequency,
                until_date,
            )
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
            messages.info(request, "Appointment Was NOT created")
            return redirect("customerdashboard")

    def handle_reschedule_get(self, request, *args, **kwargs):
        self.appointment = Appointment.objects.filter(
            customer=self.customer, provider=self.provider_user
        ).first()
        self.recurrence_form = AppointmentRecurrenceForm(
            initial={
                "recurrence": self.appointment.recurrence_frequency,
                "until_date": self.appointment.recurrence_until,
            }
        )
        if not self.appointment:
            messages.error(request, "No existing appointment found for recheduling ")
            return redirect("viewappointments")
        return self.render_template(request)

    def handle_reschedule_post(self, request, *args, **kwargs):
        self.recurrence_form = AppointmentRecurrenceForm(request.POST)
        if self.recurrence_form.is_valid():
            recurrence_frequency = self.recurrence_form.cleaned_data["recurrence"]
            until_date = self.recurrence_form.cleaned_data["until_date"]
        else:
            recurrence_frequency = self.appointment.recurrence_frequency
            until_date = self.appointment.recurrence_until

        if request.POST.get("confirm"):
            self.appointment = Appointment.objects.filter(
                customer=self.customer, provider=self.provider_user
            ).first()
            self.appointment = change_and_save_appointment(
                request,
                self.appointment,
                recurrence_frequency,
                until_date,
                self.start_datetime,
                self.end_datetime,
            )
            request.session.pop("mode", None)
            if self.appointment:
                messages.success(request, " appointment reschedule successfully ")
                return redirect("viewappointments")
            else:
                messages.error(request, "invalid stuff added")
                return redirect("viewappointments")
        if request.POST.get("cancel"):
            messages.info(request, "reschedule ancelled")
            return redirect("viewappoinments")

    def render_template(self, request, *args, **kwargs):
        return render(
            request,
            "customer/addappointment.html",
            {
                "start": self.start_datetime,
                "end": self.end_datetime,
                "form": self.recurrence_form,
                "mode": self.mode,
                "appointment": self.appointment if self.mode == "reschedule" else None,
            },
        )


addappointment = AddAppointment.as_view()


class ViewAppointments(View, LoginRequiredMixin):
    login_url = "/login/"

    def get(self, request, *args, **kwargs):

        self.myappointments = self.get_query(request, *args, **kwargs)
        paginator = Paginator(self.myappointments , 10)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        return render(
            request,
            "customer/viewappointments.html",
            {"appointments": self.myappointments,
            "page_obj": page_obj},
        )

    def post(self, request, *args, **kwargs):
        if request.POST.get("reschedule"):
            self.appointmentID = request.POST.get("reschedule")
            return self.reschedule(request, *args, **kwargs)
        elif request.POST.get("cancel"):
            self.appointmentID = request.POST.get("cancel")
            return self.cancel(request, *args, **kwargs)

    def get_query(self, request, *args, **kwargs):

        query = request.GET.get("q")
        key = f"get_appointments_for_{request.user.id}_and_{query}"
        myappointments = cache.get(key)
        if myappointments:
            return myappointments
        else:
            if query:
                myappointments = (
                    Appointment.objects.filter(
                        customer=request.user, provider__username__icontains=query
                    )
                    .order_by("-date_added")
                    .all()
                    .exclude(status="rejected")
                    .exclude(status="cancelled")
                    .exclude(status="completed")
                )
            else:

                myappointments = (
                    Appointment.objects.filter(customer=request.user)
                    .order_by("-date_added")
                    .all()
                    .exclude(status="rejected")
                    .exclude(status="cancelled")
                    .exclude(status="completed")
                )
            cache.set(key, list(myappointments), timeout=60 * 7)
            return myappointments

    def reschedule(self, request, *args, **kwargs):
        messages.warning(
            request,
            "This will change the status to Rescheduled but the event for now will remain in the calendar  because the provider will have to review the timings again ",
        )
        change_appointment = Appointment.objects.get(id=request.POST.get("reschedule"))
        if change_appointment.status != "accepted":
            messages.error(
                request, "sorry you cannot reschedule a non accepted appointment "
            )
            return redirect("viewappointments")
        else:
            return redirect("reschedule", appointment_id=self.appointmentID)

    def cancel(self, request, *args, **kwargs):
        appointment = Appointment.objects.get(id=self.appointmentID)
        count_cancel = cancellation(request.user, appointment)
        if appointment.status == "accepted":
            service = get_calendar_service(appointment.provider)
            service.events().delete(
                calendarId="primary", eventId=appointment.event_id
            ).execute()
        appointment.status = "cancelled"
        appointment.save()
        if count_cancel >= 3:
            request.user.is_active = False
            request.user.save()
            logout(request)
            messages.warning(
                request,
                "You have cancelled too many appointments in a shot span , your account has been deactivated ",
            )
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


class BookingHistoryView(LoginRequiredMixin, ListView):
    model = Appointment
    template_name = "customer/bookinghistory.html"
    context_object_name = "appointments"
    ordering = ["-date_added"]
    paginate_by = 5

    def get_queryset(self):

        return Appointment.objects.filter(customer=self.request.user).order_by(
            "-date_added"
        )


bookinghistory = BookingHistoryView.as_view()
