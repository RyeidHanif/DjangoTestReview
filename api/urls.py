from django.urls import path
from rest_framework_simplejwt.views import (TokenObtainPairView,
                                            TokenRefreshView)

from . import views

urlpatterns = [
    path("register/", views.API_signupuser),
    path("welcome/", views.API_welcome),
    path("user_profile/", views.API_user_profile),
    path("provider_appointments/", views.API_provider_appoinments),
    path("customer_appointments/", views.API_customer_appointments),
    path("provider_availability/<int:providerID>", views.API_provider_availability),
    path("provider_analytics/", views.API_provider_analytics),
    path("view_providers/", views.API_view_providers),
]
