from datetime import datetime, timedelta
from unittest.mock import ANY, MagicMock, patch

import pytest
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.utils import timezone

from main.models import (Appointment, CustomerProfile, NotificationPreferences,
                         ProviderProfile)

from .factories import (AppointmentFactory, CustomerProfileFactory,
                        NotificationPreferencesFactory, ProviderProfileFactory,
                        UserFactory)


@pytest.mark.django_db
class TestProviderDashboardView:
    @pytest.fixture
    def create_user(db):
        user = UserFactory()
        provider_profile = ProviderProfileFactory(user=user)
        customer_profile = CustomerProfileFactory(user=user)
        return user

    def test_unauthenticated_get(self, client):
        response = client.get(reverse("provider_dashboard"), follow=True)
        assert response.status_code == 200
        redirection = reverse("login") + "?next=/provider_dashboard/"
        assert (redirection, 302) in response.redirect_chain

    def test_authenticated_get(self, client, create_user):
        user = create_user
        client.force_login(user)
        response = client.get(reverse("provider_dashboard"))
        assert response.status_code == 200
        template_names = [t.name for t in response.templates]
        assert "provider/provider_dashboard.html" in template_names

    @pytest.mark.parametrize(
        "action,redirect",
        [
            ("my_profile", "user_profile"),
            ("view_analytics", "view_analytics"),
            ("view_my_appointments", "view_my_appointments"),
            ("view_pending_appointments", "view_pending_appointments"),
            ("my_availability", "my_availability"),
            ("customer_side", "customer_dashboard"),
        ],
    )
    def test_actions_post(self, client, create_user, action, redirect):
        user = create_user
        client.force_login(user)
        response = client.post(
            reverse("provider_dashboard"), data={action: 1}, follow=True
        )
        assert response.status_code == 200
        redirection = reverse(redirect)
        assert (redirection, 302) in response.redirect_chain


@pytest.mark.django_db
class TestListAcceptedAppointmentsView:

    @pytest.fixture
    def create_user(db):
        user = UserFactory()
        provider_profile = ProviderProfileFactory(user=user)
        customer_profile = CustomerProfileFactory(user=user)
        notification_settings = NotificationPreferencesFactory(user=user)
        return user

    def test_unauthenticated_get(self, client):
        response = client.get(reverse("view_my_appointments"), follow=True)
        assert response.status_code == 200
        redirection = reverse("login") + "?next=/view-my-appointments/"
        assert (redirection, 302) in response.redirect_chain

    def test_authenticated_get(self, client, create_user):
        user = create_user
        client.force_login(user)
        response = client.get(reverse("view_my_appointments"))
        assert response.status_code == 200
        template_names = [t.name for t in response.templates]
        assert "provider/view_my_appointments.html" in template_names

        assert "page_obj" in response.context

    def test_mark_completed_post_valid(self, client, create_user):
        user = create_user
        appointment = AppointmentFactory(provider=user, status="accepted")
        client.force_login(user)
        response = client.post(
            reverse("view_my_appointments"), data={"markcompleted": appointment.id}
        )
        assert response.status_code == 302
        check_appointment = Appointment.objects.get(id=appointment.id)
        assert check_appointment.status == "completed"

    def test_mark_completed_post_invalid(self, client, create_user):
        user = create_user
        client.force_login(user)
        date_start = timezone.now() + timedelta(minutes=40)
        date_end = timezone.now() + timedelta(minutes=100)
        appointment = AppointmentFactory(
            provider=user, status="accepted", date_start=date_start, date_end=date_end
        )
        response = client.post(
            reverse("view_my_appointments"),
            data={"markcompleted": appointment.id},
            follow=True,
        )
        assert response.status_code == 200

        redirect = reverse("view_my_appointments")
        assert (redirect, 302) in response.redirect_chain

    @patch("provider.views.cancellation", return_value=0)
    @patch("provider.views.GoogleCalendarClient")
    def test_cancel_appointment_post_valid(
        self, mock_calendar_client, mock_cancellation, client, create_user
    ):
        user = create_user
        client.force_login(user)
        mock_calendar_client_instance = mock_calendar_client.return_value
        mock_calendar_client_instance.delete_event.return_value = None
        appointment = AppointmentFactory(
            provider=user, status="accepted", event_id="some-event-id"
        )
        response = client.post(
            reverse("view_my_appointments"), data={"cancel": appointment.id}
        )

        appointment.refresh_from_db()

        # Check if appointment was cancelled
        assert appointment.status == "cancelled"

        # Check if GoogleCalendarClient.delete_event was called
        mock_calendar_client_instance.delete_event.assert_called_once_with(
            user, "some-event-id"
        )

        # Check redirect
        assert response.status_code == 302
        assert response.url == reverse("view_my_appointments")

    @patch("provider.views.cancellation", return_value=0)
    @patch("provider.views.GoogleCalendarClient")
    def test_invalid_cancel_appointment(
        self, mock_calendar_client_class, mock_cancellation, client, create_user
    ):
        user = create_user
        client.force_login(user)

        # Send POST with non-existent appointment ID
        response = client.post(reverse("view_my_appointments"), data={"cancel": 9999})

        assert response.status_code == 404
        mock_calendar_client_class.return_value.delete_event.assert_not_called()


@pytest.mark.django_db
class TestListPendingAppointmentsView:

    @pytest.fixture
    def create_user(self):
        user = UserFactory()
        ProviderProfileFactory(user=user)
        # Customer profile and notification settings for appointments
        customer = UserFactory()
        CustomerProfileFactory(user=customer)
        NotificationPreferencesFactory(user=customer)
        return user, customer

    def test_get_pending_appointments_view(self, client, create_user):
        provider, customer = create_user
        client.force_login(provider)
        AppointmentFactory(provider=provider, customer=customer, status="pending")

        response = client.get(reverse("view_pending_appointments"))
        assert response.status_code == 200
        assert "provider/view_pending_appointments.html" in [
            t.name for t in response.templates
        ]

    @patch("provider.views.GoogleCalendarClient")
    def test_post_accept_pending_success(
        self, mock_calendar_client, client, create_user
    ):
        provider, customer = create_user
        client.force_login(provider)
        appointment = AppointmentFactory(
            provider=provider, customer=customer, status="pending"
        )

        mock_calendar_client.return_value.create_google_calendar_event.return_value = {
            "id": "mock-event-id"
        }

        response = client.post(
            reverse("view_pending_appointments"),
            data={"accept": appointment.id},
            follow=True,
        )
        appointment.refresh_from_db()

        assert appointment.status == "accepted"
        assert appointment.event_id == "mock-event-id"
        assert ("/view-pending-appointments/", 302) in response.redirect_chain

    @patch("provider.views.GoogleCalendarClient")
    def test_post_accept_reschedule_success(
        self, mock_calendar_client, client, create_user
    ):
        provider, customer = create_user
        client.force_login(provider)
        appointment = AppointmentFactory(
            provider=provider,
            customer=customer,
            status="rescheduled",
            event_id="abc123",
        )

        response = client.post(
            reverse("view_pending_appointments"),
            data={"accept": appointment.id},
            follow=True,
        )
        appointment.refresh_from_db()

        assert appointment.status == "accepted"
        assert ("/view-pending-appointments/", 302) in response.redirect_chain
        mock_calendar_client.return_value.reschedule_google_event.assert_called_once()

    @patch("provider.views.GoogleCalendarClient")
    def test_post_reject_pending_or_reschedule(
        self, mock_calendar_client, client, create_user
    ):
        provider, customer = create_user
        client.force_login(provider)

        # Pending rejection
        pending_appt = AppointmentFactory(
            provider=provider, customer=customer, status="pending"
        )
        reschedule_appt = AppointmentFactory(
            provider=provider,
            customer=customer,
            status="rescheduled",
            event_id="abc123",
        )

        response_pending = client.post(
            reverse("view_pending_appointments"),
            data={"reject": pending_appt.id},
            follow=True,
        )
        pending_appt.refresh_from_db()
        assert pending_appt.status == "rejected"
        assert ("/view-pending-appointments/", 302) in response_pending.redirect_chain

        response_resched = client.post(
            reverse("view_pending_appointments"),
            data={"reject": reschedule_appt.id},
            follow=True,
        )
        reschedule_appt.refresh_from_db()
        assert reschedule_appt.status == "cancelled"
        assert ("/view-pending-appointments/", 302) in response_resched.redirect_chain
        mock_calendar_client.return_value.delete_event.assert_called_once()

    def test_search_pending_by_name(self, client, create_user):
        provider, customer = create_user
        client.force_login(provider)

        appt_aris = AppointmentFactory(
            provider=provider, status="pending", customer__first_name="Aris"
        )
        AppointmentFactory(
            provider=provider, status="pending", customer__first_name="Bob"
        )

        response = client.get(reverse("view_pending_appointments") + "?q=Aris")
        assert response.status_code == 200
        assert b"Aris" in response.content
        assert b"Bob" not in response.content


@pytest.mark.django_db
class TestMyAvailabilityView:
    @pytest.fixture
    def create_user(db):
        user = UserFactory()
        provider_profile = ProviderProfileFactory(user=user)
        customer_profile = CustomerProfileFactory(user=user)
        NotificationPreferencesFactory(user=user)
        return user

    def test_unauthenticated_get(self, client):
        response = client.get(reverse("my_availability"), follow=True)
        assert response.status_code == 200
        redirection = "/accounts" + reverse("login") + "?next=/my_availability"
        assert (redirection, 302) in response.redirect_chain

    def test_authenticated_get(self, client, create_user):
        user = create_user
        client.force_login(user)
        response = client.get(reverse("my_availability"))
        assert response.status_code == 200
        assert "provider/my_availability.html" in [t.name for t in response.templates]
        assert "form" in response.context


@pytest.mark.django_db
class TestProviderAnalyticsView:
    @pytest.fixture
    def create_user(db):
        user = UserFactory()
        provider_profile = ProviderProfileFactory(user=user)
        customer_profile = CustomerProfileFactory(user=user)
        NotificationPreferencesFactory(user=user)
        return user

    def test_unauthenticated_get(self, client):
        response = client.get(reverse("view_analytics"), follow=True)
        assert response.status_code == 200
        redirection = reverse("login") + "?next=/view-analytics"
        assert (redirection, 302) in response.redirect_chain

    @pytest.mark.parametrize(
        "item",
        [
            ("customers"),
            ("appointments"),
            ("statuses"),
            ("revenue"),
            ("admin_cut"),
            ("percentage_statuses_dict"),
        ],
    )
    def test_authenticated_get(self, client, create_user, item):
        user = create_user
        client.force_login(user)
        response = client.get(reverse("view_analytics"))
        assert response.status_code == 200
        assert "provider/view_analytics.html" in [t.name for t in response.templates]
        assert item in response.context
