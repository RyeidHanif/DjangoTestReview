from django.urls import path

from . import views

urlpatterns = [
    path("customerdashboard/", views.customerdashboard, name="customerdashboard"),
    path(
        "addappointment/<int:providerUserID>",
        views.addappointment,
        name="addappointment",
    ),
    path("viewproviders", views.viewproviders, name="viewproviders"),
    path("schedule/<int:providerID>", views.schedule, name="schedule"),
    path("viewappointments", views.viewappointments, name="viewappointments"),
]
