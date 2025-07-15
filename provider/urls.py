from django.urls import path

from . import views

urlpatterns = [
    path("providerdashboard/", views.providerdashboard, name="providerdashboard"),
    path(
        "view-my-appointments/", views.view_my_appointments, name="view_my_appointments"
    ),
    path(
        "view-pending-appointments/",
        views.view_pending_appointments,
        name="view_pending_appointments",
    ),
    path("view-analytics", views.viewanalytics, name="viewanalytics"),
    path("myavailability", views.myavailability, name="myavailability"),
]
