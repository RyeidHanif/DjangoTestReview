from django import forms
from django.core.exceptions import ValidationError

from main.models import Appointment, ProviderProfile


class AppointmentRecurrenceForm(forms.Form):
    """Form with a choice field to allow the user to add recrrence or leave it empty
    and a date until which the event will recur
    """

    RECURRENCE_CHOICES = [
        ("NONE", "No Recurrence"),
        ("DAILY", "Daily"),
        ("WEEKLY", "Weekly"),
        ("MONTHLY", "Monthly"),
    ]

    recurrence = forms.ChoiceField(choices=RECURRENCE_CHOICES, required=False)
    until_date = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )

    def __init__(self, *args, **kwargs):
        """
        This function overriding was required  to ensure that the user
        cannot add any recurrence until date which is before the actual appointment data
        """
        appointment_date = kwargs.pop("appointment_date", None)
        super().__init__(*args, **kwargs)
        if appointment_date:
            self.fields["until_date"].widget.attrs["min"] = appointment_date.strftime(
                "%Y-%m-%d"
            )

    def clean(self):
        cleaned_data = super().clean()
        recurrence = cleaned_data.get("recurrence")
        until_date = cleaned_data.get("until_date")

        appointment_date = self.fields["until_date"].widget.attrs.get("min")
        if appointment_date:
            # Convert string min date back to date object for comparison
            from datetime import datetime

            appointment_date_obj = datetime.strptime(
                appointment_date, "%Y-%m-%d"
            ).date()
            if until_date and until_date < appointment_date_obj:
                raise ValidationError(
                    {"until_date": "Until date cannot be before the appointment date."}
                )
        return cleaned_data
