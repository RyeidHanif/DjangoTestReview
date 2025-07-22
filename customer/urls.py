from django.urls import path

from . import views

urlpatterns = [
    path("customer_dashboard/", views.customer_dashboard, name="customer_dashboard"),
    path(
        "add_appointment/<int:providerID>",
        views.add_appointment,
        name="add_appointment",
    ),
    path("view_providers", views.view_providers, name="view_providers"),
    path("schedule/<int:providerID>", views.schedule, name="schedule"),
]
