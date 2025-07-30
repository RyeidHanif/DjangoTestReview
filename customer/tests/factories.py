from datetime import datetime, time

import factory
from django.contrib.auth.models import User
from django.utils import timezone
from faker import Faker

from main.models import (Appointment, CustomerProfile, NotificationPreferences,
                         ProviderProfile)

faker = Faker()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.LazyAttribute(
        lambda _: faker.user_name()
    )  # generates a differnt username evey time with lazy
    email = factory.LazyAttribute(
        lambda _: faker.email()
    )  # generates a different email ever ytime with lazy to avoid conflicts
    password = factory.PostGenerationMethodCall(
        "set_password", "password123"
    )  # hashes the password as django stores it hashed
    is_active = True  # my Object managers require user to be active
    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        raw_password = extracted or "password123"
        self.set_password(raw_password)
        if create:
            self.save()


class ProviderProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProviderProfile

    user = factory.SubFactory(UserFactory)
    phone_number = factory.LazyFunction(lambda: faker.phone_number()[:13])

    service_category = "doctor"
    service_name = factory.LazyAttribute(lambda _: faker.job()[:10])
    pricing_model = "fixed"
    duration_mins = 60
    google_access_token = None
    google_refresh_token = None
    google_token_expiry = None
    google_calendar_connected = False
    start_time = time(9, 0, 0)
    end_time = time(17, 0, 0)
    rate = 100.0
    buffer = 15
    profile_photo = None


class CustomerProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomerProfile

    user = factory.SubFactory(UserFactory)
    phone_number = factory.LazyFunction(lambda: faker.phone_number()[:13])


class AppointmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Appointment
        exclude = ("provider_profile", "customer_profile")

    provider_profile = factory.SubFactory(ProviderProfileFactory, user__is_active=True)
    customer_profile = factory.SubFactory(CustomerProfileFactory, user__is_active=True)
    provider = factory.SelfAttribute("provider_profile.user")
    customer = factory.SelfAttribute("customer_profile.user")

    date_start = timezone.make_aware(
        datetime(2025, 7, 28, 10, 0, 0), timezone.get_current_timezone()
    )
    date_end = timezone.make_aware(
        datetime(2025, 7, 28, 11, 0, 0), timezone.get_current_timezone()
    )
    date_added = factory.LazyFunction(timezone.now)
    status = "pending"
    event_id = None
    total_price = 3000
    special_requests = "None"
    recurrence_frequency = None
    recurrence_until = None
    cancelled_by = None
    cancelled_at = None
    bad_cancel = False


class NotificationPreferencesFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NotificationPreferences

    user = factory.SubFactory(UserFactory)
    preferences = "all"
