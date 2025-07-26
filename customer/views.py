from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import localdate, make_aware
from django.views import View
from django.views.generic import ListView, TemplateView

from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from main.calendar_client import GoogleCalendarClient
from main.models import Appointment, NotificationPreferences, ProviderProfile
from main.utils import (
    cancellation,
    force_provider_calendar,
    handle_exception,
)

from .forms import AppointmentRecurrenceForm
from .utils import (
    EmailPendingAppointment,
    EmailRescheduledAppointment,
    calculate_total_price,
    change_and_save_appointment,
    check_appointment_exists,
    create_and_save_appointment,
)


class CustomerDashboardView(LoginRequiredMixin, TemplateView):
    """
    Generic Template Vieww to allow user with customer profile to navigate the Application
    """

    login_url = "/login/"
    template_name = "customer/customer_dashboard.html"

    ACTION_MAPPING = {
        "view_providers": "view_providers",
        "view_appointments": "view_appointments",
        "my_profile": "user_profile",
        "booking_history": "booking_history",
    }

    def post(self, request, *args, **kwargs):
        for action_key, value in self.ACTION_MAPPING.items():
            if request.POST.get(action_key):
                return redirect(value)
        if request.POST.get("provider_side"):
            if hasattr(request.user, "providerprofile"):
                return redirect("provider_dashboard")
            else:
                return redirect("profile_creation")

        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Changes the Display of the provider dashboard redirection button depending on whether the user already has a provider profile or not"""
        context = super().get_context_data(**kwargs)
        context["display"] = (
            "Go to provider Dashboard"
            if hasattr(self.request.user, "providerprofile")
            else "Become a Service Provider"
        )
        return context


customer_dashboard = CustomerDashboardView.as_view()


class ListProvidersView(LoginRequiredMixin, ListView):
    """Generic List View to List All providers registered with the application"""

    model = ProviderProfile
    template_name = "customer/view_providers.html"
    context_object_name = "providers"

    def get_queryset(self):
        """Allows the searh bar to be used to search for a provider by their username"""
        query = self.request.GET.get("q")

        if query:
            try:

                return ProviderProfile.objects.filter(
                    user__username__icontains=query
                ).exclude(user=self.request.user)
            except Exception as e:
                return handle_exception(e)

        else:
            return ProviderProfile.objects.exclude(user=self.request.user)

    def post(self, request, *args, **kwargs):
        messages.info(
            request, "You are being redirected to the service providers schedule"
        )
        return redirect("schedule", providerID=request.POST.get("book_appointment"))

    def get_context_data(self, **kwargs):
        """Sends  Category Data to the template to allow the providers to be displayed , divided by category"""
        context = super().get_context_data(
            **kwargs
        )  # first get the context then add stuff to it  to pass to the template
        context["categories"] = ["doctor", "consultant", "therapist", "counsellor"]
        return context


view_providers = ListProvidersView.as_view()


class ScheduleView(LoginRequiredMixin, View):
    """
    Allows the user to view a specific provider's schedule .
    The URL includes a keyword argument for the provider profile ID of a user
    """

    login_url = "/login/"

    def dispatch(self, request, *args, **kwargs):
        """send data to both get and post functions"""
        self.provider_profile = get_object_or_404(
            ProviderProfile, id=kwargs["providerID"]
        )
        self.provider = self.provider_profile.user
        self.slot_range = 1
        self.google_client = GoogleCalendarClient()
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Use The Google Client to get a provider's available slots . in case of any error , return a JSON error response"""
        try:
            self.available_slots = self.google_client.get_available_slots(
                self.provider, self.slot_range
            )
        except RefreshError as re:
            force_provider_calendar(self.provider)
            return JsonResponse(
                {
                    "error": "refresh_token_expired",
                    "message": "Provider's Google Calendar account has expired and must be renewed.",
                },
                status=400,
            )
        except HttpError as e:
            return JsonResponse({"error": str(e)}, status=400)
        return self.render_schedule(self.available_slots)

    def post(self, request, *args, **kwargs):
        """Allow the user to choose between seeing the availabiliy of a provider for the current day or week"""
        if request.POST.get("week"):
            self.slot_range = 7
        elif request.POST.get("day"):
            self.slot_range = 1
        elif request.POST.get("slot_range"):  # hidden input
            self.slot_range = int(request.POST.get("slot_range"))

        self.available_slots = self.google_client.get_available_slots(
            self.provider, self.slot_range
        )

        if request.POST.get("add_appointment"):
            index = int(request.POST.get("add_appointment"))
            self.timeslot = self.available_slots[index]
            request.session["timeslot_tuple"] = (
                self.timeslot[0].isoformat(),
                self.timeslot[1].isoformat(),
            )

            return redirect("add_appointment", providerUserID=self.provider.id)
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


schedule = ScheduleView.as_view()


class AddAppointmentView(LoginRequiredMixin, View):
    """
    Allows the User to Create and Reschedule Appointments depending upon the mode
    - Normal Mode signifies the user is creating an appointment and will call on all the functions related to creation
    - Reschedule Mode signifies the user is rescheduling an appointment and will call on all the rescheduling function
    It has been divided into 4 parts each dealing with one method of each mode
    """

    def dispatch(self, request, *args, **kwargs):
        """Sends data which is required by all or greater than 1 of the methods"""
        self.mode = request.session.get("mode", "normal")
        self.timeslot = request.session.get("timeslot_tuple", [])
        self.provider_user = get_object_or_404(User, id=kwargs["providerUserID"])
        self.provider = ProviderProfile.objects.get(user=self.provider_user)
        self.customer = request.user
        self.start_datetime = datetime.fromisoformat(self.timeslot[0])
        self.end_datetime = datetime.fromisoformat(self.timeslot[1])
        self.total_price = calculate_total_price(self.provider)

        self.recurrence_form = AppointmentRecurrenceForm(
            appointment_date=self.start_datetime
        )
        self.appointment = None
        self.google_client = GoogleCalendarClient()
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """checks between the modes and calls functions accordingly"""
        if self.mode == "normal":
            return self.handle_normal_get(request, *args, **kwargs)
        elif self.mode == "reschedule":
            return self.handle_reschedule_get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """checks between the modes and calls functions accordingly"""
        if self.mode == "normal":
            return self.handle_normal_post(request, *args, **kwargs)
        elif self.mode == "reschedule":
            return self.handle_reschedule_post(request, *args, **kwargs)

    def handle_normal_get(self, request, *args, **kwargs):
        """displays the appointment recurrence form with the recurrence date limit and checks if an appointment already exists"""
        self.recurrence_form = AppointmentRecurrenceForm(
            appointment_date=self.start_datetime
        )

        if not check_appointment_exists(self.customer, self.provider_user):
            messages.warning(
                request,
                " You already have an appointment with this provider , Cancel or complete thatone first",
            )

            return redirect("view_providers")

        return self.render_template(request)

    def handle_normal_post(self, request, *args, **kwargs):
        """
        Creates a new appointment from the customer to the provider with the Pending Status
        - Confirm button is  pressed after completing the recurrence form and adding special requests if needed
        - total price is calculated
        - special requests are gotten from the user
        - the utility function for create_and_save_appointment is called and parameters passed
        - an email is sent to the provider that a new appointment has been created depending on their notification settings
        """
        self.recurrence_form = AppointmentRecurrenceForm(
            request.POST, appointment_date=self.start_datetime
        )

        if request.POST.get("confirm"):
            recurrence_frequency = None
            until_date = None
            if self.recurrence_form.is_valid():
                recurrence_frequency = self.recurrence_form.cleaned_data["recurrence"]
                until_date = self.recurrence_form.cleaned_data["until_date"]

            self.total_price = calculate_total_price(
                self.provider,
                recurrence_frequency=recurrence_frequency,
                until_date=until_date,
            )

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
            return redirect("customer_dashboard")
        elif request.POST.get("cancel"):
            messages.info(request, "Appointment Was NOT created")
            return redirect("customer_dashboard")

    def handle_reschedule_get(self, request, *args, **kwargs):
        """Creates a prefilled recurrence form with original details and checks if the appointment exists or not"""
        self.appointment = Appointment.objects.filter(
            customer=self.customer, provider=self.provider_user
        ).first()
        self.recurrence_form = AppointmentRecurrenceForm(
            initial={
                "recurrence": self.appointment.recurrence_frequency,
                "until_date": self.appointment.recurrence_until,
            },
            appointment_date=self.start_datetime,
        )
        if not self.appointment:
            messages.error(request, "No existing appointment found for recheduling ")
            return redirect("view_appointments")
        return self.render_template(request)

    def handle_reschedule_post(self, request, *args, **kwargs):
        """
        creates the recurrence form with post data and the recurrence date limit
        - if the recurrence has been changed then it is used , other wise original appoinmtnet details are used
        - total price is recalculated in case of any changes
        - once the confirm button is pressed the appointment is officially changed in the database and its status changed to rescheduled
        the rescheduled appointment appears with the pending appointments for the provider . in the case that it is rejected , the status
        is changed to accepted with the original date and time
        - After the rescheduling is done , the mode is popped from the session to prevent conflicts later
        """
        self.recurrence_form = AppointmentRecurrenceForm(
            request.POST, appointment_date=self.start_datetime
        )
        if self.recurrence_form.is_valid():
            recurrence_frequency = self.recurrence_form.cleaned_data["recurrence"]
            until_date = self.recurrence_form.cleaned_data["until_date"]

        else:
            recurrence_frequency = self.appointment.recurrence_frequency
            until_date = self.appointment.recurrence_until

        self.total_price = calculate_total_price(
            self.provider,
            recurrence_frequency=recurrence_frequency,
            until_date=until_date,
        )

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
                self.total_price,
            )
            request.session.pop("mode", None)
            if self.appointment:
                messages.success(request, " appointment reschedule successfully ")
                return redirect("view_appointments")
            else:
                messages.error(request, "invalid stuff added")
                return redirect("view_appointments")
        if request.POST.get("cancel"):
            messages.info(request, "reschedule ancelled")
            return redirect("view_appoinments")

    def render_template(self, request, *args, **kwargs):
        return render(
            request,
            "customer/add_appointment.html",
            {
                "start": self.start_datetime,
                "end": self.end_datetime,
                "form": self.recurrence_form,
                "mode": self.mode,
                "appointment": self.appointment if self.mode == "reschedule" else None,
            },
        )


add_appointment = AddAppointmentView.as_view()


class ViewAppointmentsView(LoginRequiredMixin, View):
    """Allows the customer to view all their appointments"""

    login_url = "/login/"

    def get(self, request, *args, **kwargs):
        """paginates the results  by 10 appointments per page"""

        self.myappointments = self.get_query(request, *args, **kwargs)
        paginator = Paginator(self.myappointments, 10)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        return render(
            request,
            "customer/view_appointments.html",
            {"appointments": self.myappointments, "page_obj": page_obj},
        )

    def post(self, request, *args, **kwargs):

        if request.POST.get("reschedule"):
            self.appointmentID = request.POST.get("reschedule")
            return self.reschedule(request, *args, **kwargs)
        elif request.POST.get("cancel"):
            self.appointmentID = request.POST.get("cancel")
            return self.cancel(request, *args, **kwargs)

    def get_query(self, request, *args, **kwargs):
        """Allows the use of a search bar to search using the provider's username"""

        query = request.GET.get("q")

        EXCLUDED_STATUES = ["rejected", "cancelled", "completed"]
        if query:
            return (
                Appointment.objects.filter(
                    customer=request.user, provider__username__icontains=query
                )
                .order_by("-date_added")
                .all()
                .exclude(status__in=EXCLUDED_STATUES)
            )
        else:

            return (
                Appointment.objects.filter(customer=request.user)
                .order_by("-date_added")
                .all()
                .exclude(status__in=EXCLUDED_STATUES)
            )

    def reschedule(self, request, *args, **kwargs):
        """
        once the reschedule button is pressed for an appointment , this method is called
        -Displays a warning to the user to ensure they know that the status will change
        - forbid the user from rescheduling any appointment that has not been accepted
        """
        messages.warning(
            request,
            "This will change the status to Rescheduled but the event for now will remain in the calendar  because the provider will have to review the timings again ",
        )

        change_appointment = get_object_or_404(
            Appointment, id=request.POST.get("reschedule")
        )

        if change_appointment.status != "accepted":
            messages.error(
                request, "sorry you cannot reschedule a non accepted appointment "
            )
            return redirect("view_appointments")
        else:
            return redirect("reschedule", appointment_id=self.appointmentID)

    def cancel(self, request, *args, **kwargs):
        """
        When the cancel button is pressed this method is called to cancel the appointment
        - uses the calendar client to erase the event from google calendar if it was there in the first place
        - Checks if the user has cancelled more than 3 appointments within 12 hours of appointment time within the last 30 days
        - if yes , the user is set to inactive and hence cannot perform any actions .
        - if not , one cancellation is added by calling the cancellation utility"""
        calendar_client = GoogleCalendarClient()
        appointment = get_object_or_404(Appointment, id=self.appointmentID)
        count_cancel = cancellation(request, request.user, appointment)
        if appointment.status == "accepted":
            try:
                service = calendar_client.get_calendar_service(appointment.provider)
                service.events().delete(
                    calendarId="primary", eventId=appointment.event_id
                ).execute()

            except RefreshError as re:
                force_provider_calendar(appointment.provider)
                return JsonResponse(
                    {
                        "error": "refresh_token_expired",
                        "message": "Provider's Google Calendar account has expired and must be renewed.",
                    },
                    status=400,
                )
            except HttpError as e:
                return JsonResponse({"error": str(e)}, status=400)

        appointment.status = "cancelled"
        appointment.save()
        if not request.user.is_superuser:
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
        return redirect("view_appointments")


view_appointments = ViewAppointmentsView.as_view()


# very simple . left this as FBV . doesnt fit in any generic CBVs and View CBV will just have more boilerplate
@login_required(login_url="/login/")
def reschedule(request, appointment_id):
    """Simple Intermediary page to confirm rescheduling with user and set the Session"""
    change_appointment = get_object_or_404(Appointment, id=appointment_id)
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
    """Allow the customer to view all their booking history , with appointments of all statuses"""

    model = Appointment
    template_name = "customer/booking_history.html"
    context_object_name = "appointments"
    ordering = ["-date_added"]

    paginate_by = 5

    def get_queryset(self):

        return Appointment.objects.filter(customer=self.request.user).order_by(
            "-date_added"
        )


booking_history = BookingHistoryView.as_view()
