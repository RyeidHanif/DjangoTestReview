from django import forms

from main.models import Appointment, ProviderProfile


class AppointmentRecurrenceForm(forms.Form):
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
