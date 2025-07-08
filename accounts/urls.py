from django.contrib.auth import views as auth_views
from django.urls import include, path

from . import views

urlpatterns = [
    path("signup/", views.signup , name = "signup")
    
]


       