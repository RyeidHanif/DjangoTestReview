from django import forms
from django.core.exceptions import ValidationError

from .models import Appointment, CustomerProfile, ProviderProfile


class ProviderForm(forms.ModelForm):
    """
    model form to get data related to provider and both profile creation
    """

    class Meta:
        model = ProviderProfile
        fields = [
            "service_category",
            "service_name",
            "pricing_model",
            "duration_mins",
            "start_time",
            "end_time",
            "rate",
            "buffer",
            "profile_photo",
        ]
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if start_time and end_time and start_time >= end_time:
            raise ValidationError("Start time must be before end time.")

        return cleaned_data


class CreateCustomerProfileForm(forms.Form):
    phone_number = forms.IntegerField()
