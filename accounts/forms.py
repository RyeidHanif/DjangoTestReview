from django import forms
from django.contrib.auth.forms import SetPasswordForm, UserCreationForm
from django.contrib.auth.models import User
from django.forms.widgets import FileInput

from main.models import NotificationPreferences, ProviderProfile

NOTIFICATION_CHOICES = [("all", "All"), ("reminders", "Reminders"), ("none", "None")]


class SignUpForm(UserCreationForm):
    """
    Default User Creation Model form with extra fields

    the profile choices system allows the user to choose what they
    want to do here so that they can be redirected easily to the profile
    creation system before login
    """

    phone_number = forms.CharField(required=True)

    class Meta:
        """connect form to model User and customize fields"""

        model = User
        fields = ["email", "username", "password1", "password2"]


class SetPasswordForm(SetPasswordForm):
    class Meta:
        model = User
        fields = ["new_password1", "new_password2"]


class ChangeNotificationPreferencesForm(forms.ModelForm):
    preferences = forms.ChoiceField(
        widget=forms.RadioSelect, choices=NOTIFICATION_CHOICES
    )

    class Meta:
        model = NotificationPreferences
        fields = ["preferences"]


class ProfilePhotoForm(forms.ModelForm):
    class Meta:
        model = ProviderProfile
        fields = ["profile_photo"]
        widgets = {
            "profile_photo": FileInput(attrs={"class": "form-control"}),
        }
