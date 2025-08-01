from django.urls import path
from rest_framework_simplejwt.views import (TokenObtainPairView,
                                            TokenRefreshView)

from . import views

urlpatterns = [
    path("register/", views.API_signupuser, name= "api_register"),
    path("welcome/", views.API_welcome, name="api_welcome"),
    path("user_profile/", views.API_user_profile, name="api_user_profile"),
    path("provider_appointments/", views.API_provider_appoinments , name= "api_provider_appointments"),
    path("customer_appointments/", views.API_customer_appointments, name="api_customer_appointments"),
    path("provider_availability/<int:providerID>", views.API_provider_availability, name="api_provider_availability"),
    path("provider_analytics/", views.API_provider_analytics, name="api_provider_analytics"),
    path("view_providers/", views.API_view_providers, name="api_view_providers"),
]
