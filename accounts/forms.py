from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


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
        fields = ["email", "username", "password1", "password2", "phone_number"]
