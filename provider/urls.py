from django.urls import path

from . import views

urlpatterns = [
    path("provider_dashboard/", views.provider_dashboard, name="provider_dashboard")
]
