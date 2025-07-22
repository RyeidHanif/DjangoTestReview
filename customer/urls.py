from django.urls import path

from . import views

urlpatterns = [
    path("customer_dashboard/", views.customer_dashboard, name="customer_dashboard"),
    path(
        "add_appointment/<int:providerUserID>",
        views.add_appointment,
        name="add_appointment",
    ),
    path("view_providers", views.view_providers, name="view_providers"),
    path("schedule/<int:providerID>", views.schedule, name="schedule"),
    path("view_appointments", views.view_appointments, name="view_appointments"),
    path("reschedule/<appointment_id>", views.reschedule, name="reschedule"),
    path("booking_history/", views.booking_history, name="booking_history"),
]
