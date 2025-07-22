from django.urls import path

from . import views

urlpatterns = [
    path("provider_dashboard/", views.provider_dashboard, name="provider_dashboard"),
    path(
        "view-my-appointments/", views.view_my_appointments, name="view_my_appointments"
    ),
    path(
        "view-pending-appointments/",
        views.view_pending_appointments,
        name="view_pending_appointments",
    ),
    path("view-analytics", views.view_analytics, name="view_analytics"),
    path("my_availability", views.my_availability, name="my_availability"),
]
