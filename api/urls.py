from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

urlpatterns = [
    path("register/", views.signupuser, name="register"),
    path("welcome/", views.welcome, name="welcome"),
]
