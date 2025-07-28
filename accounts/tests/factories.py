from datetime import datetime, time

import factory
import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from faker import Faker

from main.models import ProviderProfile

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
