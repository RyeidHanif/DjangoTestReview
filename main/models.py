# Create your models here.
import datetime
import uuid

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.timezone import localtime

SERVICE_CHOICES = [
    ("doctor", "Doctor"),
    ("consultant", "Consultant"),
    ("therapist", "Therapist"),
    ("counsellor", "Counsellor"),
]

STATUS_CHOICES = [
    ("pending", "Pending"),
    ("accepted", "Accepted"),
    ("rejected", "Rejected"),
    ("completed", "Completed"),
    ("cancelled", "Cancelled"),
    ("rescheduled", "Rescheduled"),
]

NOTIFICATION_CHOICES = [("all", "All"), ("reminders", "Reminders"), ("none", "None")]

default_start = datetime.time(9, 0, 0)
default_end = datetime.time(17, 0, 0)


class ActiveProviderManager(models.Manager):
    """Make sure that when we get objects , only those are queried with active users"""

    def get_queryset(self):
        return super().get_queryset().filter(user__is_active=True)


class ActiveAppointmentManager(models.Manager):
    """Makes sure that when we get appointment objects , only those with active providers are queried"""

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(customer__is_active=True, provider__is_active=True)
        )


class ProviderProfile(models.Model):
    """
    provider profile model to get the user's service data and add google calendar tokens

    """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=13)
    service_category = models.CharField(choices=SERVICE_CHOICES)
    service_name = models.CharField(max_length=20)
    pricing_model = models.CharField(
        choices=[("hourly", "Hourly"), ("fixed", "Fixed")], default="fixed"
    )
    duration_mins = models.IntegerField()
    google_access_token = models.TextField(blank=True, null=True)
    google_refresh_token = models.TextField(blank=True, null=True)
    google_token_expiry = models.DateTimeField(blank=True, null=True)
    google_calendar_connected = models.BooleanField(default=False)
    start_time = models.TimeField(default=default_start)
    end_time = models.TimeField(default=default_end)
    rate = models.FloatField(default=0)
    buffer = models.IntegerField(default=0)
    profile_photo = models.ImageField(default=None, null=True, blank=True)

    objects = ActiveProviderManager()
    all_objects = models.Manager()

    def __str__(self):
        return f"provider profile of user {self.user.username}"


class CustomerProfile(models.Model):
    """
    model to get user data for customer profile
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=13)

    def __str__(self):
        return f"customer profile of user {self.user.username}"


class Appointment(models.Model):
    """
    model to add data regarding appointments
    """

    provider = models.ForeignKey(
        User, related_name="provider_appointments", on_delete=models.CASCADE
    )
    customer = models.ForeignKey(
        User, related_name="customer_appointments", on_delete=models.CASCADE
    )
    date_start = models.DateTimeField()
    date_end = models.DateTimeField()
    date_added = models.DateTimeField(auto_now_add=True)
    status = models.CharField(choices=STATUS_CHOICES, max_length=12, default="pending")
    event_id = models.TextField(blank=True, null=True)
    total_price = models.FloatField(default=0)
    special_requests = models.TextField(default="None")
    recurrence_frequency = models.CharField(max_length=10, null=True, blank=True)
    recurrence_until = models.DateField(blank=True, null=True)
    cancelled_by = models.ForeignKey(
        User, default=None, blank=True, null=True, on_delete=models.CASCADE
    )
    cancelled_at = models.DateTimeField(blank=True, null=True)
    bad_cancel = models.BooleanField(default=False)

    objects = ActiveAppointmentManager()
    all_objects = models.Manager()

    def clean(self):
        if self.status != "cancelled":
            if self.bad_cancel or self.cancelled_at or self.cancelled_by:
                raise ValidationError(
                    "Cancellation fields can only be set if the appointment is cancelled."
                )

    def __str__(self):
        return f"Appointment by {self.customer.username} for {self.provider.username} on {self.date_start}"


class AnalyticsApi(models.Model):
    """
    JWT authentication for API for each user to get their data as JSON
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)


class NotificationPreferences(models.Model):
    """
    Allow the user to change notification prferences

    Includes  3 levels :
    1. All notifications
    2. Only google calendar Reminders
    3. None

    Args:
    user : One to one field to user for easy access
    preferences : the actual user choice , defaulting to all
    """

    user = models.OneToOneField(
        User, related_name="notification_settings", on_delete=models.CASCADE
    )
    preferences = models.CharField(
        max_length=11, choices=NOTIFICATION_CHOICES, default="all"
    )
