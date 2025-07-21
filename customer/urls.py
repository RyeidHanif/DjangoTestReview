from django.urls import path

from . import views

urlpatterns = [
    path("customer_dashboard/", views.customer_dashboard, name="customer_dashboard"),
    path(
        "addappointment/<int:providerUserID>",
        views.addappointment,
        name="addappointment",
    ),
    path("viewproviders", views.viewproviders, name="viewproviders"),
    path("schedule/<int:providerID>", views.schedule, name="schedule"),
    path("viewappointments", views.viewappointments, name="viewappointments"),
    path("reschedule/<appointment_id>", views.reschedule, name="reschedule"),
    path("bookinghistory/", views.bookinghistory, name="bookinghistory"),
]
