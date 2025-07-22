from django.contrib.auth.models import User
from django.shortcuts import render
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from .permissions import CustomHasProviderProfile
from customer.utils import get_available_slots
from django.db.models import Sum
from datetime import datetime, timezone
from django.utils.timezone import localtime

from rest_framework.exceptions import ValidationError

# Create your views here.
from main.models import AnalyticsApi, ProviderProfile, Appointment

from .serializers import (
    RegisterSerializer,
    ProviderProfileSerializer,
    AppointmentSerializer,
    ProviderAnalyticsSerializer,
    ViewAllProvidersSerializer,
)
from collections import Counter


class SignUpUser(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer


signupuser = SignUpUser.as_view()


class WelcomeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": f"Welcome, {request.user.username}!"})


welcome = WelcomeView.as_view()


class MyProfile(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, CustomHasProviderProfile]
    serializer_class = ProviderProfileSerializer

    def get_object(self):
        return self.request.user.providerprofile


my_profile = MyProfile.as_view()


class MyProviderAppointments(generics.ListAPIView):
    permission_classes = [IsAuthenticated, CustomHasProviderProfile]
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        user = self.request.user
        return Appointment.objects.filter(provider=user)
    
    def list(self, request , *args , **kwargs):
        queryset= self.get_queryset()
        serializer= self.get_serializer(queryset , many=True)
        wrapped_data = [{"appointment": piece} for piece in serializer.data]
        return Response(wrapped_data)


my_provider_appoinments = MyProviderAppointments.as_view()


class MyCustomerAppointments(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        user = self.request.user

        return Appointment.objects.filter(provider=user)
    
    def list(self, request , *args , **kwargs):
        queryset= self.get_queryset()
        serializer= self.get_serializer(queryset , many=True)
        wrapped_data = [{"appointment": piece} for piece in serializer.data]
        return Response(wrapped_data)


my_customer_appointments = MyCustomerAppointments.as_view()

class APIProviderAvailability(APIView):
    permission_classes = [IsAuthenticated]

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

        provider = User.objects.select_related("providerprofile").get(id=providerID)
        if not hasattr(provider, "providerprofile"):
            return Response({"error": "Provider profile missing"}, status=400)
        elif not provider.providerprofile.google_calendar_connected:
            raise ValidationError(
                {"Unavailable": "Google Calendar of the provider is not connected"}
            )

        slots = get_available_slots(provider, slot_range)

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

        return Response({"available_slots": formatted_slots})


API_provider_availability = APIProviderAvailability.as_view()


class APIProviderAnalytics(APIView):
    permission_classes = [IsAuthenticated, CustomHasProviderProfile]

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


class APIViewProviders(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ViewAllProvidersSerializer

    def get_queryset(self):
        return ProviderProfile.objects.all()
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        wrapped_data = [{"provider": item} for item in serializer.data] # wrap each whole provider and their details under the provider key 
        return Response(wrapped_data)


API_view_providers = APIViewProviders.as_view()
