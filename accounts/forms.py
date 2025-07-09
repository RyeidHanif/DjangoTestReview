from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class SignUpForm(UserCreationForm):

    PROFILE_CHOICES = [
        ("customer", "Customer"),
        ("provider", "Provider"),
        ("both", "Both"),
    ]
    profile_choice = forms.ChoiceField(
        choices=PROFILE_CHOICES, widget=forms.RadioSelect
    )
    phone_number = forms.CharField(required=True)

    class Meta:
        model = User
        fields = ["email", "username", "password1", "password2", "profile_choice"]
