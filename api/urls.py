from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

urlpatterns = [
    path("register/", views.signupuser),
    path("welcome/", views.welcome),
    path("myprofile/", views.my_profile),
    path("my_provider_appointments/", views.my_provider_appoinments),
    path("my_customer_appointments/", views.my_customer_appointments),
    path("provider_availability/<int:providerID>", views.API_provider_availability),
    path("provider_analytics/", views.API_provider_analytics),
    path("view_providers/", views.API_view_providers),
]
