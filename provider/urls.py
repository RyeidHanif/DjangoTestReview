from django.urls import path

from . import views

urlpatterns = [
    path("providerdashboard/", views.providerdashboard, name="providerdashboard")
]
