from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("redirectiondashboard/", views.redirectiondashboard, name="redirectiondashboard"),
    path("connect_calendar", views.connect_to_calendar, name="connect_to_calendar"),
    path("connect-google/", views.connect_google, name="connect_google"),
    path("google/oauth2callback/", views.oauth2callback, name="oauth2callback"),
    path("cancellation/" , views.cancellation_policy , name="cancellation_policy"),
    path("admin_dashboard/", views.admin_dashboard , name="admin_dashboard"),
    path("view_customer_profile/<int:userID>", views.view_customer_profile , name="view_customer_profile"),
    path("view_provider_profile/<int:userID>" , views.view_provider_profile, name="view_provider_profile"),
    path("create_profile/", views.profile_creation, name="profile_creation"),
]
