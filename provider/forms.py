from django import forms


class AvailabilityForm(forms.Form):
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


class SendNoteForm(forms.Form):
    note = forms.CharField(max_length = 100)