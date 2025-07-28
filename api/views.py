from collections import Counter
from datetime import datetime, timezone

from django.contrib.auth.models import User
from django.db.models import Sum
from django.shortcuts import render
from django.utils.timezone import localtime
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from main.calendar_client import GoogleCalendarClient
# Create your views here.
from main.models import AnalyticsApi, Appointment, ProviderProfile

from .permissions import CustomHasProviderProfile
from .serializers import (AppointmentSerializer, ProviderAnalyticsSerializer,
                          ProviderProfileSerializer, RegisterSerializer,
                          SlotSerializer, ViewAllProvidersSerializer,
                          WelcomeSerializer)


@extend_schema(tags=["Registration"])
class SignUpUser(generics.CreateAPIView):
    """
    Allows the user to sign up

    The User Sends a POST request with the following details to this endpoint :
     - username
     - email
     - password

    if the user does not already exist , a new user is created"""

    queryset = User.objects.all()
    serializer_class = RegisterSerializer


API_signupuser = SignUpUser.as_view()


@extend_schema(tags=["Registration"])
class WelcomeView(APIView):
    """simple welcome view to allow a logged in user  to access the API
    only accepts GET methods
    """

    permission_classes = [IsAuthenticated]
    serializer_class = WelcomeSerializer

    def get(self, request):
        data = {"message": f"Welcome, {request.user.username}!"}
        serializer = self.serializer_class(data)
        return Response(serializer.data)


API_welcome = WelcomeView.as_view()


@extend_schema(tags=["Personal"])
class Profile(generics.RetrieveAPIView):
    """
    endpoint to allow an authenticated user to view their own service provider profile
    only accepts GET method"""

    permission_classes = [IsAuthenticated, CustomHasProviderProfile]
    serializer_class = ProviderProfileSerializer

    def get_object(self):
        return self.request.user.providerprofile


API_user_profile = Profile.as_view()


@extend_schema(tags=["Personal"])
class ProviderAppointments(generics.ListAPIView):
    """
    Allows user to access all their own appointments
    only accepts GET method
    """

    permission_classes = [IsAuthenticated, CustomHasProviderProfile]
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        user = self.request.user
        return Appointment.objects.filter(provider=user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        wrapped_data = [{"appointment": piece} for piece in serializer.data]
        return Response(wrapped_data)


API_provider_appoinments = ProviderAppointments.as_view()


@extend_schema(tags=["Personal"])
class CustomerAppointments(generics.ListAPIView):
    """
    allows a customer to view their own appointments
    Only Accepts GET Method
    """

    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        user = self.request.user

        return Appointment.objects.filter(provider=user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        wrapped_data = [{"appointment": piece} for piece in serializer.data]
        return Response(wrapped_data)


API_customer_appointments = CustomerAppointments.as_view()


@extend_schema(tags=["Services"])
class APIProviderAvailability(APIView):
    """
    Allows a user to get a provider's available slots

    the User sends a GET request with the following url parameters :
    - the id of the provider
    - the slot range which must be an integer between 1 and 7
    this allows the user to get all the  available slots of that provider
    for 1 - 7 days
    """

    permission_classes = [IsAuthenticated]
    serializer_class = SlotSerializer

    def get_slot_range(self, request):
        try:
            slot_range = int(request.query_params.get("slot_range", 1))
        except (ValueError, TypeError):
            raise ValidationError({"slot_range": "Must be an integer between 1 and 7"})

        if not 1 <= slot_range <= 7:
            raise ValidationError({"slot_range": "Must be between 1 and 7"})
        return slot_range

    def get(self, request, providerID):
        slot_range = self.get_slot_range(request)

        try:
            provider = User.objects.select_related("providerprofile").get(id=providerID)
        except User.DoesNotExist:
            raise NotFound("Provider with this ID does not exist.")

        if not hasattr(provider, "providerprofile"):
            return Response({"error": "Provider profile missing"}, status=400)
        elif not provider.providerprofile.google_calendar_connected:
            raise ValidationError(
                {"Unavailable": "Google Calendar of the provider is not connected"}
            )
        calendar_client = GoogleCalendarClient()
        slots = calendar_client.get_available_slots(provider, slot_range)

        formatted_slots = [
            {
                "start_date": localtime(slot[0]).strftime("%Y-%m-%d"),
                "start_time": localtime(slot[0]).strftime("%H:%M:%S"),
                "end_date": localtime(slot[1]).strftime("%Y-%m-%d"),
                "end_time": localtime(slot[1]).strftime("%H:%M:%S"),
                "timezone": localtime(slot[0]).strftime("%Z"),
            }
            for slot in slots
        ]

        serializer = self.serializer_class(formatted_slots, many=True)
        return Response({"Available slots": serializer.data})


API_provider_availability = APIProviderAvailability.as_view()


@extend_schema(tags=["Services"])
class APIProviderAnalytics(APIView):
    """
    Provider Accesses this endpoint to view analytics data regarding their appointments
    """

    permission_classes = [IsAuthenticated, CustomHasProviderProfile]
    serializer_class = ProviderAnalyticsSerializer

    def get(self, request, *args, **kwargs):
        provider = request.user
        appointments = Appointment.objects.filter(provider=provider).order_by(
            "-date_added"
        )
        total_appointments = appointments.count()

        revenue_data = appointments.filter(
            status__in=["completed", "accepted"]
        ).aggregate(Sum("total_price"))
        total_revenue = revenue_data["total_price__sum"] or 0

        admin_revenue = 0.05 * total_revenue
        my_revenue = total_revenue - admin_revenue

        statuses = Counter()
        for appointment in appointments:
            statuses[appointment.status] += 1

        data = {
            "provider": provider,
            "appointments": appointments,
            "total_appointments": total_appointments,
            "admin_revenue": admin_revenue,
            "my_revenue": my_revenue,
            "statuses": statuses,
        }

        serializer = ProviderAnalyticsSerializer(data)
        return Response(serializer.data)


API_provider_analytics = APIProviderAnalytics.as_view()


@extend_schema(tags=["Services"])
class APIViewProviders(generics.ListAPIView):
    """
    Allows any logged in user to view all the service providers in the applicatios
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ViewAllProvidersSerializer

    def get_queryset(self):
        return ProviderProfile.objects.all()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        wrapped_data = [
            {"provider": item} for item in serializer.data
        ]  # wrap each whole provider and their details under the provider key
        return Response(wrapped_data)


API_view_providers = APIViewProviders.as_view()
