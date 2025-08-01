import pytest
from django.contrib.auth.models import User
from rest_framework.exceptions import ValidationError

from main.models import Appointment, ProviderProfile
from api.serializers import (
    RegisterSerializer,
    ProviderAnalyticsSerializer,
    SlotSerializer,
)

from datetime import date, time
from .factories import UserFactory , ProviderProfileFactory , AppointmentFactory , CustomerProfileFactory


@pytest.mark.django_db
class TestRegisterSerializer:

    def test_register_serializer_creates_user_with_hashed_password(self):
        data = {
            "username": "tester",
            "email": "tester@example.com",
            "password": "securepassword123"
        }
        serializer = RegisterSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        user = serializer.save()
        assert isinstance(user, User)
        assert user.username == "tester"
        assert user.email == "tester@example.com"
        assert user.check_password("securepassword123")  # ensure password is hashed


@pytest.mark.django_db
class TestProviderAnalyticsSerializer:
    @pytest.fixture
    def provider_user(db):
        user = UserFactory()
        ProviderProfileFactory(user=user)
        CustomerProfileFactory(user=user)
        return user 

    def test_valid_data_returns_serialized_output(self, provider_user):
        appts = [
            AppointmentFactory(provider=provider_user,status= "completed"),
            AppointmentFactory(provider=provider_user, status="cancelled"),
        ]

        data = {
            "provider": provider_user,
            "appointments": appts,
            "total_appointments": 2,
            "admin_revenue": 50.0,
            "my_revenue": 200.0,
            "statuses": {"completed": 1, "cancelled": 1},
        }

        serializer = ProviderAnalyticsSerializer(data)
        result = serializer.data

        assert result["provider"] == provider_user.username
        assert result["total_appointments"] == 2
        assert result["my_revenue"] == 200.0
        assert result["statuses"]["cancelled"] == 1
        assert len(result["appointments"]) == 2


class TestSlotSerializer:

    def test_slot_serializer_valid_data(self):
        data = {
            "start_date": date(2025, 8, 2),
            "start_time": time(10, 0),
            "end_date": date(2025, 8, 2),
            "end_time": time(10, 30),
            "timezone": "Asia/Karachi"
        }

        serializer = SlotSerializer(data=data)
        assert serializer.is_valid()
        validated = serializer.validated_data
        assert validated["start_time"] == time(10, 0)
        assert validated["timezone"] == "Asia/Karachi"

    def test_slot_serializer_missing_field(self):
        data = {
            "start_date": date(2025, 8, 2),
            "start_time": time(10, 0),
            "end_date": date(2025, 8, 2),
            "end_time": time(10, 30),
            
        }
        serializer = SlotSerializer(data=data)
        assert not serializer.is_valid()
        assert "timezone" in serializer.errors
