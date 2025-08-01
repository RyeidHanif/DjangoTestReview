from django.contrib import admin
from django.core import serializers
from django.core.mail import send_mail
from django.http import HttpResponse
from django.utils.safestring import mark_safe
from django.utils.timezone import (activate, get_current_timezone, localdate,
                                   localtime, make_aware, now)

from main.calendar_client import GoogleCalendarClient

from .models import (AnalyticsApi, Appointment, CustomerProfile,
                     NotificationPreferences, ProviderProfile)


class ProviderProfileAdmin(admin.ModelAdmin):
    """Allows for Admin users to be able to see more information on each provider profile and show their available slots for the day"""

    actions = ["show_available_slots"]
    list_display = ["user", "service_category", "service_name", "rate", "duration_mins"]
    list_filter = ["service_category"]
    empty_value_display = "N/A"
    radio_fields = {"service_category": admin.HORIZONTAL}

    @admin.action(
        description="Show available slots for today (for 1 selected provider)"
    )
    def show_available_slots(self, request, queryset):
        """Uses the available slots method of the google calendar client to get a provider's available slots for the day"""
        if queryset.count() != 1:
            self.message_user(
                request, "Please select exactly one provider.", level="error"
            )
            return

        provider = queryset.first()
        provider_user = provider.user
        calendar_client = GoogleCalendarClient()

        slots = calendar_client.get_available_slots(provider_user, 1)

        if not slots:
            self.message_user(request, "No available slots for today.")
            return

        slot_items = "".join(
            f"<li>{localtime(start).strftime('%I:%M %p')} – {localtime(end).strftime('%I:%M %p')}</li>"
            for start, end in slots
        )
        html = f"<strong>Available slots today:</strong><ul>{slot_items}</ul>"

        self.message_user(request, mark_safe(html))


class CustomerProfileAdmin(admin.ModelAdmin):
    """Displays extra information for each customer profile on the main dashboard"""

    list_display = ["user", "phone_number"]


class AppointmentAdmin(admin.ModelAdmin):
    """
    Add extra information and actions for each appointments

    - Order by the starting date of the appointment
    -displays extra information on the ain dashboard wtih list_display
    - change the  empty value placeholder
    - add and group more fields when admin opens that admin model in the dashboard
    - add a radio choice field  for status of an appointment
    - alow appointment to be searched using the provider's email
    - allow the list of appoinmtnets to be filtered by status and/or provider
    - add 2 actions :
    1. mark an appointment as accepted
    2. send reminder emails to all the users the admin selected
    """

    date_hierarchy = "date_start"
    list_display = ["provider", "customer", "date_start", "date_end"]
    empty_value_display = "-empty-"
    fields = [
        "provider",
        "customer",
        ("date_start", "date_end"),
        ("recurrence_frequency", "recurrence_until"),
        "total_price",
        "status",
    ]
    radio_fields = {"status": admin.VERTICAL}
    search_fields = ["provider__email"]
    actions = ["send_reminders", "mark_as_accepted"]
    list_filter = ["status", "provider"]

    @admin.action(description="mark selected appointments as accepted")
    def mark_as_accepted(self, request, queryset):
        updated = queryset.update(status="accepted")
        self.message_user(request, f"{updated} appointments marked as confirmed ")

    @admin.action(
        description="Send reminder emails to users who have upcoming appointments "
    )
    def send_reminders(self, request, queryset):
        for appointment in queryset:
            send_mail(
                "Reminder: Your Appointment",
                f"Hi {appointment.customer.username}, don't forget your appointment on {localtime(appointment.date_start)}.",
                "admin@APSS.com",
                [appointment.customer.email],
            )

            send_mail(
                "Reminder : Appointment coming up ",
                f"Hi {appointment.provider.username} , don't forget , you have an appointment coming up on {localtime(appointment.date_start)}.",
                "admin@APSS.com",
                [appointment.provider.email],
            )
        self.message_user(request, f"{queryset.count()} reminders sent.")


class NotificationPreferencesAdmin(admin.ModelAdmin):
    """Add extra information for notification preferenes"""

    radio_fields = {"preferences": admin.HORIZONTAL}
    list_display = ["user", "preferences"]
    list_filter = ["preferences"]


admin.site.register(ProviderProfile, ProviderProfileAdmin)
admin.site.register(CustomerProfile, CustomerProfileAdmin)
admin.site.register(Appointment, AppointmentAdmin)
admin.site.register(AnalyticsApi)
admin.site.register(NotificationPreferences, NotificationPreferencesAdmin)


# Register your models here.
