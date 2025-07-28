from django import forms

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
