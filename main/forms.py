from django import forms

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
        ]
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }
