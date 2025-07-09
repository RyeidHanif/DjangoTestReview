from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model


User = get_user_model()

class SignUpForm(UserCreationForm):

    class Meta:
        model = User
        fields = ['email', 'username', 'phoneno', 'user_type', 'password1', 'password2']
