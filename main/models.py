# Create your models here.
import uuid

from django.contrib.auth.models import User
from django.db import models

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
]


class ProviderProfile(models.Model):
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
    calendarID = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"provider profile of user {self.user.username}"


class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=13)

    def __str__(self):
        return f"customer profile of user {self.user.username}"


class Appointment(models.Model):
    provider = models.ForeignKey(
        User, related_name="provider_appointments", on_delete=models.CASCADE
    )
    customer = models.ForeignKey(
        User, related_name="customer_appointments", on_delete=models.CASCADE
    )
    date = models.DateTimeField()
    date_added = models.DateTimeField(auto_now_add=True)
    status = models.CharField(choices=STATUS_CHOICES, max_length=12, default="pending")
