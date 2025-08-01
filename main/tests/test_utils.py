from datetime import timedelta

import pytest
from django.utils.timezone import now

from main.models import Appointment
from main.utils import cancellation

from .factories import (AppointmentFactory, CustomerProfileFactory,
                        ProviderProfileFactory, UserFactory)


@pytest.mark.django_db
class TestCancellationUtils:
    @pytest.fixture
    def create_user(db):
        user = UserFactory()
        ProviderProfileFactory(user=user)
        CustomerProfileFactory(user=user)
        return user

    def test_good_cancel_does_not_increase_bad_count(self, create_user):
        user = create_user
        appointment = AppointmentFactory(
            customer=user,
            date_start=now() + timedelta(days=2),  # > 12 hours away
            status="cancelled",
        )

        count = cancellation(None, user, appointment)
        assert count == 0
        appointment.refresh_from_db()
        assert appointment.bad_cancel is False

    def test_bad_cancel_increases_bad_count(self, create_user):
        user = create_user
        appointment = AppointmentFactory(
            customer=user,
            date_start=now() + timedelta(hours=5),  # < 12 hours
            status="cancelled",
        )

        count = cancellation(None, user, appointment)
        assert count == 1
        appointment.refresh_from_db()
        assert appointment.bad_cancel is True
        assert appointment.cancelled_by == user
        assert appointment.cancelled_at is not None

    def test_multiple_bad_cancels_within_30_days(self, create_user):
        user = create_user

        for i in range(3):
            AppointmentFactory(
                customer=user,
                date_start=now() + timedelta(hours=5),
                cancelled_by=user,
                cancelled_at=now(),
                status="cancelled",
                bad_cancel=True,
            )

        new_appointment = AppointmentFactory(
            customer=user,
            date_start=now() + timedelta(hours=5),
            status="cancelled",
        )

        count = cancellation(None, user, new_appointment)
        assert count == 4  # including the one we just cancelled

    def test_old_bad_cancels_are_not_counted(self, create_user):
        user = create_user

        AppointmentFactory(
            customer=user,
            date_start=now() - timedelta(days=40),
            cancelled_by=user,
            cancelled_at=now() - timedelta(days=40),
            status="cancelled",
            bad_cancel=True,
        )

        new_appointment = AppointmentFactory(
            customer=user,
            date_start=now() + timedelta(hours=5),
            status="cancelled",
        )

        count = cancellation(None, user, new_appointment)
        assert count == 1  # only new one should be counted

    def test_cancelled_by_and_cancelled_at_are_set_correctly(self, create_user):
        user = create_user
        appointment = AppointmentFactory(
            customer=user,
            date_start=now() + timedelta(hours=3),
            status="cancelled",
        )

        cancellation(None, user, appointment)
        appointment.refresh_from_db()
        assert appointment.cancelled_by == user
        assert appointment.cancelled_at is not None
