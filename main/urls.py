from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("redirectiondashboard/", views.redirectiondashboard, name="redirectiondashboard"),
    path("create_profile/<str:n>", views.profile_creation, name="profile_creation"),
    path("connect_calendar", views.connect_to_calendar, name="connect_to_calendar"),
    path("connect-google/", views.connect_google , name ="connect_google"),
    path("google/oauth2callback/", views.oauth2callback , name = "oauth2callback")
]
