from django import forms
from django.core.exceptions import ValidationError


class AvailabilityForm(forms.Form):
    """Form to allow the user to enter when they are not available"""

    cause = forms.CharField(max_length=100)
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}), required=True
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}), required=True
    )
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={"type": "time"}), required=True
    )
    end_time = forms.TimeField(
        widget=forms.TimeInput(attrs={"type": "time"}), required=True
    )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if start_date == end_date:
            if start_time >= end_time:
                raise ValidationError(
                    "the Starting time cannot be before the ending time "
                )
        elif start_date >= end_date:
            raise ValidationError("The Starting date cannot be after the ending date ")

        return cleaned_data


class SendNoteForm(forms.Form):
    note = forms.CharField(max_length=100)
