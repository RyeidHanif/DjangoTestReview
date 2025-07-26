from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import JsonResponse
# Create your views here.
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import (activate, get_current_timezone, localdate,
                                   localtime, make_aware, now)
from django.views import View
from django.views.generic import ListView, TemplateView
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from logging_conf import logger
from main.calendar_client import GoogleCalendarClient
from main.models import Appointment, NotificationPreferences, ProviderProfile
from main.utils import cancellation, force_provider_calendar

from .forms import AvailabilityForm, SendNoteForm
from .utils import (EmailCancelledAppointment, EmailConfirmedAppointment,
                    EmailDeclinedAppointment, EmailRescheduleDeclined,
                    SendEmailRescheduleAccepted)


class ProviderDashboardView(LoginRequiredMixin, TemplateView):
    login_url = "/login/"
    template_name = "provider/provider_dashboard.html"

    ACTION_MAPPING = {
        "my_profile": "user_profile",
        "view_analytics": "view_analytics",
        "view_my_appointments": "view_my_appointments",
        "view_pending_appointments": "view_pending_appointments",
        "my_availability": "my_availability",
    }

    def post(self, request, *args, **kwargs):
        for key, value in self.ACTION_MAPPING.items():
            if request.POST.get(key):
                return redirect(value)
        return self.get(request, *args, **kwargs)


provider_dashboard = ProviderDashboardView.as_view()


class ListAcceptedAppointmentsView(LoginRequiredMixin, View):

    login_url = "/login/"

    def get(self, request, *args, **kwargs):
        query = request.GET.get("q")

        if query:
            my_appointments = Appointment.objects.filter(
                provider=request.user,
                status="accepted",
                customer__username__icontains=query,
            ).order_by("-date_added")
        else:
            my_appointments = Appointment.objects.filter(
                provider=request.user, status="accepted"
            ).order_by("-date_added")

        paginator = Paginator(my_appointments, 10)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        return render(
            request,
            "provider/view_my_appointments.html",
            {"page_obj": page_obj},
        )

    def post(self, request, *args, **kwargs):
        calendar_client = GoogleCalendarClient()
        if request.POST.get("cancel"):
            cancel_appointment = get_object_or_404(
                Appointment, id=request.POST.get("cancel")
            )

            to_email = cancel_appointment.customer.email
            customer = cancel_appointment.customer
            provider = cancel_appointment.provider
            cancel_appointment.status = "cancelled"
            try:
                calendar_client.delete_event(request.user, cancel_appointment.event_id)

            except RefreshError as re:
                force_provider_calendar(cancel_appointment.provider)
                return JsonResponse(
                    {
                        "error": "refresh_token_expired",
                        "message": "Provider's Google Calendar account has expired and must be renewed.",
                    },
                    status=400,
                )
            except HttpError as e:
                return JsonResponse({"error": str(e)}, status=400)

            cancel_appointment.save()
            if customer.notification_settings.preferences == "all":
                EmailCancelledAppointment(request, customer, provider, to_email)
            count_cancel = cancellation(request, request.user, cancel_appointment)
            if count_cancel >= 3:

                request.user.is_active = False
                request.user.save()
                logout(request)
                messages.warning(
                    request,
                    "you cancelled too many apointments after deadline in a short span of time ",
                )
                return redirect("home")
            else:
                return redirect("view_my_appointments")

        if request.POST.get("markcompleted"):

            appointment = get_object_or_404(
                Appointment, id=request.POST.get("markcompleted")
            )

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


view_my_appointments = ListAcceptedAppointmentsView.as_view()


class ListPendingAppointmentsView(LoginRequiredMixin, View):
    login_url = "/login/"

    def get(self, request, *args, **kwargs):
        query = request.GET.get("q")

        if query:
            my_appointments = Appointment.objects.filter(
                status__in=["pending", "rescheduled"],
                provider=request.user,
                customer__username__icontains=query,
            )
        else:
            my_appointments = Appointment.objects.filter(
                status__in=["pending", "rescheduled"], provider=request.user
            )

        paginator = Paginator(my_appointments, 10)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        return render(
            request,
            "provider/view_pending_appointments.html",
            {"page_obj": page_obj},
        )

    def post(self, request, *args, **kwargs):
        if request.POST.get("reject"):

            appointment = get_object_or_404(Appointment, id=request.POST.get("reject"))

            return self.reject_appointment(request, appointment)

        if request.POST.get("accept"):

            appointment = get_object_or_404(Appointment, id=request.POST.get("accept"))
            return self.accept_appointment(request, appointment)

        return redirect("view_pending_appointments")

    def reject_appointment(self, request, appointment):
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
            appointment.status = "accepted"
            appointment.save()
            messages.info(request, "reschedule rejected successfully ")
            if appointment.customer.notification_settings.preferences == "all":
                EmailRescheduleDeclined(
                    request,
                    appointment.customer,
                    appointment.provider,
                    appointment.date_start,
                    appointment.date_end,
                    appointment.customer.email,
                )
            return redirect("view_pending_appointments")

    def accept_appointment(self, request, appointment):
        calendar_client = GoogleCalendarClient()
        if appointment.status == "pending":
            appointment.status = "accepted"

            summary = f"Appointment with {appointment.customer.username}"

            timeslot = (
                localtime(appointment.date_start).isoformat(),
                localtime(appointment.date_end).isoformat(),
            )

            try:
                event = calendar_client.create_google_calendar_event(
                    appointment.provider,
                    timeslot,
                    summary,
                    appointment.customer.email,
                    appointment.recurrence_frequency,
                    appointment.recurrence_until,
                )

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
            try:
                calendar_client.reschedule_google_event(
                    request.user,
                    appointment.event_id,
                    localtime(appointment.date_start).isoformat(),
                    localtime(appointment.date_end).isoformat(),
                    appointment.recurrence_frequency,
                    appointment.recurrence_until,
                )

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

            if appointment.customer.notification_settings.preferences == "all":
                SendEmailRescheduleAccepted(
                    request,
                    appointment.customer,
                    appointment.provider,
                    appointment.date_start,
                    appointment.date_end,
                    appointment.customer.email,
                )
                appointment.save()
            messages.success(request, "Reschedule Accepted and will happen ")
            return redirect("view_pending_appointments")


view_pending_appointments = ListPendingAppointmentsView.as_view()


class MyAvailabilityView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        self.form = AvailabilityForm()

        return render(request, "provider/my_availability.html", {"form": self.form})

    def post(self, request, *args, **kwargs):
        calendar_client = GoogleCalendarClient()
        self.form = AvailabilityForm(request.POST)
        if self.form.is_valid():
            start_date = self.form.cleaned_data["start_date"]
            end_date = self.form.cleaned_data["end_date"]
            start_time = self.form.cleaned_data["start_time"]
            end_time = self.form.cleaned_data["end_time"]
            cause = self.form.cleaned_data["cause"]
            start_datetime = make_aware(
                datetime.combine(start_date, start_time),
                timezone=get_current_timezone(),
            )
            end_datetime = make_aware(
                datetime.combine(end_date, end_time), timezone=get_current_timezone()
            )
            start_datetime_iso = start_datetime.isoformat()
            end_datetime_iso = end_datetime.isoformat()
            try:
                calendar_client.create_availability_block(
                    request, request.user, cause, start_datetime_iso, end_datetime_iso
                )

            except RefreshError as re:
                force_provider_calendar(request.user)
                return JsonResponse(
                    {
                        "error": "refresh_token_expired",
                        "message": "Provider's Google Calendar account has expired and must be renewed.",
                    },
                    status=400,
                )
            except HttpError as e:
                return JsonResponse({"error": str(e)}, status=400)

            return redirect("my_availability")


my_availability = MyAvailabilityView.as_view()


class ViewAnalytics(LoginRequiredMixin, View):
    login_url = "/login/"

    def get(self, request, *args, **kwargs):
        revenue = 0
        myappointments = Appointment.objects.select_related("customer").filter(
            provider=request.user
        )
        total_statuses = 0
        percentage_statuses_dict = {}
        statuses = {
            "pending": 0,
            "accepted": 0,
            "rejected": 0,
            "cancelled": 0,
            "completed": 0,
            "rescheduled": 0,
        }
        customers = []
        for appointment in myappointments:
            statuses[appointment.status] += 1
            total_statuses += 1
            customers.append(appointment.customer.username)
            if appointment.status in ["accepted", "completed"]:
                revenue += appointment.total_price

        admin_cut = 0.05 * revenue
        for key, value in statuses.items():
            if total_statuses != 0:
                percentage = (value / total_statuses) * 100
            else:
                percentage = 0
            percentage_statuses_dict[key] = percentage
        return render(
            request,
            "provider/view_analytics.html",
            {
                "customers": customers,
                "appointments": myappointments,
                "statuses": statuses,
                "revenue": revenue,
                "admin_cut": admin_cut,
                "percentage_statuses_dict": percentage_statuses_dict,
            },
        )


view_analytics = ViewAnalytics.as_view()
