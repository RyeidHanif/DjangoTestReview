import pytest
from .factories import UserFactory , ProviderProfileFactory , CustomerProfileFactory , AppointmentFactory , NotificationPreferencesFactory
from main.models import ProviderProfile , CustomerProfile , Appointment , NotificationPreferences

from django.urls import reverse
from django.contrib.auth.models import User
      
from unittest.mock import patch, MagicMock, ANY 
from django.contrib.messages import get_messages


from django.utils import timezone 
from datetime import datetime, timedelta
from customer.utils import check_appointment_exists, calculate_total_price


@pytest.mark.django_db
class TestCheckAppointmentExistsUtility:
    @pytest.fixture
    def create_users(db):
        provider = UserFactory()
        ProviderProfileFactory(user=provider)
        CustomerProfileFactory(user=provider)

        customer = UserFactory()
        CustomerProfileFactory(user=customer)
        return provider,customer
    @pytest.mark.parametrize("status, is_valid",[
        ("pending", True),
        ("accepted", True),
        ("rescheduled", True),
        ("cancelled", False),
        ("rejected", False),
        ("completed", False),
    ])
    def test_with_appointment_exists(self ,  create_users, status, is_valid):
        provider, customer = create_users
        appointment = AppointmentFactory(status=status , customer=customer ,provider=provider, date_start= timezone.now() , date_end = timezone.now() + timedelta(minutes=40))
        does_it_not_exist = check_appointment_exists(customer , provider)
        assert does_it_not_exist is not is_valid



@pytest.mark.django_db
class TestCalculateTotalPrice:
    @pytest.fixture
    def create_users_fixed(db):
        provider = UserFactory()
        ProviderProfileFactory(user=provider, rate=5000 , pricing_model="fixed", duration_mins = 60)
        CustomerProfileFactory(user=provider)

        customer = UserFactory()
        CustomerProfileFactory(user=customer)
        return provider,customer
    @pytest.fixture
    def create_users_hourly(db):
        provider = UserFactory()
        ProviderProfileFactory(user=provider, rate=5000 , pricing_model="hourly", duration_mins = 60)
        CustomerProfileFactory(user=provider)

        customer = UserFactory()
        CustomerProfileFactory(user=customer)
        return provider,customer

    
    def test_total_price_without_recurrence_fixed(self, create_users_fixed):
        provider , customer = create_users_fixed
        appointment = AppointmentFactory(provider=provider , customer=customer)
        price = calculate_total_price(provider.providerprofile)
        assert price == provider.providerprofile.rate
    

    def test_total_price_without_recurrence_hourly(self , create_users_hourly):
        provider , customer = create_users_hourly
        appointment = AppointmentFactory(provider=provider , customer=customer)
        price = calculate_total_price(provider.providerprofile)
        assert price == provider.providerprofile.rate * (provider.providerprofile.duration_mins //60)
    

    @pytest.mark.parametrize("recurrence, days, expected_occurrences", [
        ("DAILY", 5, 6),   # today + 5 = 6 occurrences
        ("DAILY", 0, 1),
        ("DAILY", 10, 11),
    ])
    def test_total_price_daily(self, create_users_fixed, recurrence, days, expected_occurrences):
        provider, customer = create_users_fixed
        until_date = timezone.now() + timezone.timedelta(days=days)
        until_date = until_date.date()

        expected_price = provider.providerprofile.rate * expected_occurrences
        price = calculate_total_price(
            provider=provider.providerprofile,
            recurrence_frequency=recurrence,
            until_date=until_date
        )
        assert price == expected_price

    @pytest.mark.parametrize("recurrence, days, expected_occurrences", [
        ("WEEKLY", 7, 2),    # today + 7 = 2 weeks = 2 occurrences
        ("WEEKLY", 14, 3),
        ("WEEKLY", 0, 1),
    ])
    def test_total_price_weekly(self, create_users_fixed, recurrence, days, expected_occurrences):
        provider, customer = create_users_fixed
        until_date = timezone.now() + timezone.timedelta(days=days)
        until_date = until_date.date()

        expected_price = provider.providerprofile.rate * expected_occurrences
        price = calculate_total_price(
            provider=provider.providerprofile,
            recurrence_frequency=recurrence,
            until_date=until_date
        )
        assert price == expected_price

    @pytest.mark.parametrize("recurrence, months_delta, expected_occurrences", [
        ("MONTHLY", 0, 1),
        ("MONTHLY", 1, 2),
        ("MONTHLY", 2, 3),
    ])
    def test_total_price_monthly(self, create_users_fixed, recurrence, months_delta, expected_occurrences):
        provider, customer = create_users_fixed
        now = timezone.now()
        until_date = now + timezone.timedelta(days=months_delta * 30)  # approximation
        until_date = until_date.date()

        expected_price = provider.providerprofile.rate * expected_occurrences
        price = calculate_total_price(
            provider=provider.providerprofile,
            recurrence_frequency=recurrence,
            until_date=until_date
        )
        assert price == expected_price




