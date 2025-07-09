from django import forms

from .models import Appointment, CustomerProfile, ProviderProfile


class ProviderForm(forms.ModelForm):
    class Meta:
        model = ProviderProfile
        fields = ["service_category", "service_name", "pricing_model", "duration_mins"]
