from datetime import datetime
from unittest.mock import ANY, MagicMock, patch

import pytest
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.urls import reverse
from django.utils import timezone

from main.models import (Appointment, CustomerProfile, NotificationPreferences,
                         ProviderProfile)

from .factories import (AppointmentFactory, CustomerProfileFactory,
                        NotificationPreferencesFactory, ProviderProfileFactory,
                        UserFactory)


@pytest.mark.django_db
class TestCustomerDashboard:
    @pytest.fixture
    def create_user_details(db):
        user = UserFactory()
        provider_profile = ProviderProfileFactory(user=user)
        customer_profile = CustomerProfileFactory(user=user)
        notiications = NotificationPreferencesFactory(user=user)
        return user

    @pytest.mark.parametrize(
        "action,redirect",
        [
            ("view_providers", "view_providers"),
            ("view_appointments", "view_appointments"),
            ("my_profile", "user_profile"),
            ("booking_history", "booking_history"),
        ],
    )
    def test_action_mapping(self, client, action, redirect, create_user_details):
        user = create_user_details
        client.force_login(user)
        response = client.post(reverse("customer_dashboard"), {action: 1}, follow=True)
        assert response.status_code == 200
        assert response.redirect_chain == [(reverse(redirect), 302)]

    def test_get_data(self, client, create_user_details):
        user = create_user_details
        client.force_login(user)
        response = client.get(reverse("customer_dashboard"))
        assert response.status_code == 200
        template_names = [t.name for t in response.templates]
        assert "customer/customer_dashboard.html" in template_names

        assert "display" in response.context

    def test_unauthenticated_user_get(self, client, create_user_details):
        user = create_user_details

        response = client.get(reverse("customer_dashboard"), follow=True)
        assert response.status_code == 200
        assert response.redirect_chain == [("/login/?next=/customer_dashboard/", 302)]


@pytest.mark.django_db
@patch("main.calendar_client.GoogleCalendarClient.get_available_slots")
class TestListProvidersView:
    @pytest.fixture
    def create_user_details(db):
        user = UserFactory()
        provider_profile = ProviderProfileFactory(user=user)
        customer_profile = CustomerProfileFactory(user=user)
        notiications = NotificationPreferencesFactory(user=user)
        return user

    def test_unauthenticated_Get(self, mock_get_slots, client, create_user_details):
        user = create_user_details
        response = client.get(reverse("view_providers"), follow=True)
        assert response.status_code == 200
        assert response.redirect_chain == [
            ("/accounts/login/?next=/view_providers/", 302)
        ]

    def test_get_data(self, mock_get_slots, client, create_user_details):
        user = create_user_details
        client.force_login(user)
        response = client.get(reverse("view_providers"))
        assert response.status_code == 200
        assert "categories" in response.context
        assert "providers" in response.context
        assert user not in response.context["providers"]

    @pytest.mark.django_db(transaction=True, reset_sequences=True)
    def test_post_redirect(self, mock_get_slots, client, create_user_details):

        tz = timezone.get_current_timezone()

        mock_slots = [
            (
                timezone.make_aware(datetime(2025, 7, 30, 9, 0, 0), tz),
                timezone.make_aware(datetime(2025, 7, 30, 9, 30, 0), tz),
            ),
            (
                timezone.make_aware(datetime(2025, 7, 30, 10, 0, 0), tz),
                timezone.make_aware(datetime(2025, 7, 30, 10, 30, 0), tz),
            ),
        ]
        user = create_user_details
        other_user = UserFactory()
        other_provider = ProviderProfileFactory(
            user=other_user, google_calendar_connected=True
        )
        client.force_login(user)
        mock_get_slots.return_value = mock_slots
        response = client.post(
            reverse("view_providers"),
            data={"book_appointment": other_provider.id},  # <-- required for redirect
            follow=True,
        )
        expected_redirect = reverse(
            "schedule", kwargs={"providerID": other_provider.user.id}
        )

        assert response.status_code == 200

        assert (expected_redirect, 302) in response.redirect_chain


@pytest.mark.django_db
class TestScheduleView:
    @pytest.fixture
    def create_user_details(db):
        user = UserFactory()
        provider_profile = ProviderProfileFactory(user=user)
        customer_profile = CustomerProfileFactory(user=user)
        notiications = NotificationPreferencesFactory(user=user)
        return user

    def test_unauthentiated_get(self, client, create_user_details):
        other_provider = create_user_details
        provider_id = other_provider.providerprofile.id
        response = client.get(
            reverse("schedule", kwargs={"providerID": provider_id}), follow=True
        )
        assert response.status_code == 200
        expected_redirect = f"/login/?next=/schedule/{provider_id}/"
        assert (expected_redirect, 302) in response.redirect_chain

    @patch("main.calendar_client.GoogleCalendarClient.get_available_slots")
    def test_authenticated_get(self, mock_available_slots, client, create_user_details):
        mock_available_slots.return_value = []
        user = create_user_details
        other_provider = ProviderProfileFactory(google_calendar_connected=True)
        client.force_login(user)
        response = client.get(
            reverse("schedule", kwargs={"providerID": other_provider.id})
        )
        assert response.status_code == 200
        template_names = [t.name for t in response.templates]
        assert "customer/schedule.html" in template_names
        assert "available_slots" in response.context
        assert "provider" in response.context
        assert "slot_range" in response.context

        assert response.context["provider"] == other_provider.user

    @patch("main.calendar_client.GoogleCalendarClient.get_available_slots")
    def test_authenticated_post_week(
        self, mock_calendar_slots, client, create_user_details
    ):
        mock_calendar_slots.return_value = []
        user = create_user_details
        client.force_login(user)

        provider = ProviderProfileFactory(google_calendar_connected=True)
        url = reverse("schedule", kwargs={"providerID": provider.id})

        response = client.post(url, data={"week": "1"})

        assert response.status_code == 200

        assert "slot_range" in response.context
        assert response.context["slot_range"] == 7

    @patch("main.calendar_client.GoogleCalendarClient.get_available_slots")
    def test_authenticated_post_day(
        self, mock_calendar_slots, client, create_user_details
    ):
        mock_calendar_slots.return_value = []
        user = create_user_details
        client.force_login(user)

        provider = ProviderProfileFactory(google_calendar_connected=True)
        url = reverse("schedule", kwargs={"providerID": provider.id})

        response = client.post(url, data={"day": "1"})

        assert response.status_code == 200

        assert "slot_range" in response.context
        assert response.context["slot_range"] == 1

    @patch("main.calendar_client.GoogleCalendarClient.get_available_slots")
    @pytest.mark.django_db(transaction=True, reset_sequences=True)
    def test_post_add_appointment(
        self, mock_calendar_slots, client, create_user_details
    ):
        user = create_user_details
        mock_calendar_slots.return_value = [
            (
                timezone.make_aware(
                    datetime(2025, 7, 30, 9, 0, 0),
                    timezone=timezone.get_current_timezone(),
                ),
                timezone.make_aware(
                    datetime(2025, 7, 30, 9, 30, 0),
                    timezone=timezone.get_current_timezone(),
                ),
            )
        ]
        client.force_login(user)

        provider = ProviderProfileFactory(google_calendar_connected=True)
        url = reverse("schedule", kwargs={"providerID": provider.id})
        response = client.post(url, {"add_appointment": "0"}, follow=True)
        assert response.status_code == 200
        expected_url = reverse(
            "add_appointment", kwargs={"providerUserID": provider.id}
        )
        assert (expected_url, 302) in response.redirect_chain


@pytest.mark.django_db
@patch("main.calendar_client.GoogleCalendarClient")  # adjust patch if used in your view
class TestAddAppointmentView:

    @pytest.fixture(autouse=True)
    def user_and_provider(self, db):
        self.user = UserFactory()
        self.provider_user = UserFactory()
        ProviderProfileFactory(user=self.provider_user)
        return self.user, self.provider_user

    @pytest.fixture(autouse=True)
    def setup_session(self, client):
        session = client.session
        session["timeslot_tuple"] = (
            timezone.now().isoformat(),
            (timezone.now() + timezone.timedelta(minutes=30)).isoformat(),
        )
        session.save()

    def test_dispatch_sets_attributes(self, mock_calendar_client, client):
        url = reverse(
            "add_appointment", kwargs={"providerUserID": self.provider_user.id}
        )
        client.force_login(self.user)
        response = client.get(url)
        assert response.status_code in (200, 302)

    def test_get_normal_mode_no_existing_appointment(
        self, mock_calendar_client, client
    ):
        url = reverse(
            "add_appointment", kwargs={"providerUserID": self.provider_user.id}
        )
        client.force_login(self.user)

        with patch("customer.utils.check_appointment_exists", return_value=True):
            response = client.get(url)
            assert response.status_code == 200
            assert "form" in response.context

    def test_get_normal_mode_existing_appointment_redirects(
        self, mock_calendar_client, client
    ):
        url = reverse(
            "add_appointment", kwargs={"providerUserID": self.provider_user.id}
        )
        client.force_login(self.user)

        with patch("customer.views.check_appointment_exists", return_value=False):
            response = client.get(url, follow=True)
            final_url = response.redirect_chain[-1][0]
            assert final_url.endswith(reverse("view_providers"))

    def test_post_normal_mode_confirm_creates_and_redirects(
        self, mock_calendar_client, client
    ):
        url = reverse(
            "add_appointment", kwargs={"providerUserID": self.provider_user.id}
        )
        client.force_login(self.user)

        with patch(
            "customer.views.AppointmentRecurrenceForm"
        ) as mock_form_class, patch(
            "customer.views.create_and_save_appointment"
        ) as mock_create_appointment, patch(
            "customer.views.calculate_total_price", return_value=100
        ):

            # Mock form instance
            mock_form = MagicMock()
            mock_form.is_valid.return_value = True
            mock_form.cleaned_data = {"recurrence": None, "until_date": None}
            mock_form_class.return_value = mock_form

            response = client.post(
                url, data={"confirm": "true", "special_requests": "please be on time"}
            )
            assert response.status_code == 302
            assert response.url == reverse("customer_dashboard")
            mock_create_appointment.assert_called_once()

    def test_post_normal_mode_cancel_redirects(self, mock_calendar_client, client):
        url = reverse(
            "add_appointment", kwargs={"providerUserID": self.provider_user.id}
        )
        client.force_login(self.user)

        response = client.post(url, data={"cancel": "true"}, follow=True)
        assert response.status_code == 200
        assert response.redirect_chain[-1][0].endswith(reverse("customer_dashboard"))

    def test_get_reschedule_mode_existing_appointment(
        self, mock_calendar_client, client
    ):
        url = reverse(
            "add_appointment", kwargs={"providerUserID": self.provider_user.id}
        )
        client.force_login(self.user)

        session = client.session
        session["mode"] = "reschedule"
        session.save()

        mock_appointment = MagicMock(
            recurrence_frequency="weekly", recurrence_until="2025-12-31"
        )
        with patch("customer.views.Appointment.objects.filter") as mock_filter:
            mock_filter.return_value.first.return_value = mock_appointment
            response = client.get(url)
            assert response.status_code == 200
            assert "form" in response.context

    def test_get_reschedule_mode_no_appointment_redirects(
        self, mock_calendar_client, client
    ):
        url = reverse(
            "add_appointment", kwargs={"providerUserID": self.provider_user.id}
        )
        client.force_login(self.user)

        session = client.session
        session["mode"] = "reschedule"
        session.save()

        with patch("customer.views.Appointment.objects.filter") as mock_filter:
            mock_filter.return_value.first.return_value = None
            response = client.get(url, follow=True)
            assert response.redirect_chain[-1][0].endswith(reverse("view_appointments"))

    def test_post_reschedule_mode_confirm(self, mock_calendar_client, client):
        url = reverse(
            "add_appointment", kwargs={"providerUserID": self.provider_user.id}
        )
        client.force_login(self.user)

        session = client.session
        session["mode"] = "reschedule"
        session.save()

        mock_appointment = MagicMock()
        with patch(
            "customer.views.AppointmentRecurrenceForm"
        ) as mock_form_class, patch(
            "customer.views.Appointment.objects.filter"
        ) as mock_filter, patch(
            "customer.views.change_and_save_appointment"
        ) as mock_change_appointment:

            mock_form = MagicMock()
            mock_form.is_valid.return_value = True
            mock_form.cleaned_data = {"recurrence": None, "until_date": None}
            mock_form_class.return_value = mock_form

            mock_filter.return_value.first.return_value = mock_appointment
            mock_change_appointment.return_value = mock_appointment

            response = client.post(url, data={"confirm": "true"})
            assert response.status_code == 302
            assert response.url == reverse("view_appointments")

            # Need to check session popping - reload session:
            # Workaround: after redirect, session may not be updated in test client immediately
            session = client.session
            assert "mode" not in session

    def test_post_reschedule_mode_cancel_redirects(self, mock_calendar_client, client):
        url = reverse(
            "add_appointment", kwargs={"providerUserID": self.provider_user.id}
        )
        client.force_login(self.user)

        session = client.session
        session["mode"] = "reschedule"
        session.save()

        response = client.post(url, data={"cancel": "true"}, follow=True)
        assert response.status_code == 200
        assert response.redirect_chain[-1][0].endswith(reverse("view_appointments"))


@pytest.mark.django_db
class TestViewAppointmentsView:
    @pytest.fixture
    def create_user_details(db):
        user = UserFactory()
        provider_profile = ProviderProfileFactory(user=user)
        customer_profile = CustomerProfileFactory(user=user)
        notiications = NotificationPreferencesFactory(user=user)
        return user

    def test_unauthenticated_get(self, client, create_user_details):
        user = create_user_details
        response = client.get(reverse("view_appointments"), follow=True)
        assert response.status_code == 200
        redirection = "/login/?next=/view_appointments/"
        assert (redirection, 302) in response.redirect_chain

    @pytest.mark.parametrize(
        "status,is_valid",
        [
            ("pending", True),
            ("accepted", True),
            ("rejected", False),
            ("rescheduled", True),
            ("completed", False),
            ("cancelled", False),
        ],
    )
    def test_authenticated_get(self, client, create_user_details, status, is_valid):
        user = create_user_details
        client.force_login(user)
        appointment = AppointmentFactory(customer=user, status=status)
        response = client.get(reverse("view_appointments"))
        assert response.status_code == 200
        if is_valid:
            assert appointment in response.context["page_obj"]
        else:
            assert appointment not in response.context["page_obj"]

    def test_reschedule_post_valid(self, client, create_user_details):
        user = create_user_details
        appointment = AppointmentFactory(status="accepted")
        client.force_login(user)
        response = client.post(
            reverse("view_appointments"), {"reschedule": appointment.id}, follow=True
        )
        assert response.status_code == 200
        redirection = reverse("reschedule", kwargs={"appointment_id": appointment.id})
        assert (redirection, 302) in response.redirect_chain

    def test_reschedule_post_invalid(self, client, create_user_details):
        user = create_user_details
        appointment = AppointmentFactory(customer=user, status="pending")
        client.force_login(user)
        response = client.post(
            reverse("view_appointments"), {"reschedule": appointment.id}, follow=True
        )
        assert response.status_code == 200
        redirection = reverse("view_appointments")
        assert (redirection, 302) in response.redirect_chain

    @patch("customer.views.cancellation", return_value=0)
    @patch("customer.views.GoogleCalendarClient.get_calendar_service")
    @pytest.mark.parametrize(
        "status",
        [
            ("accepted"),
            ("pending"),
        ],
    )
    def test_cancel_post_appointment(
        self, mock_get_service, mock_cancellation, client, create_user_details, status
    ):
        user = create_user_details
        # Use factory or save explicitly
        appointment = AppointmentFactory(status=status, customer=user)

        client.force_login(user)

        mock_service = mock_get_service.return_value
        mock_events = mock_service.events.return_value
        mock_delete = mock_events.delete.return_value
        mock_delete.execute.return_value = None

        response = client.post(
            reverse("view_appointments"), {"cancel": appointment.id}, follow=True
        )

        appointment.refresh_from_db()
        assert response.status_code == 200 or 302
        assert appointment.status == "cancelled"
        mock_cancellation.assert_called_once_with(
            ANY, user, appointment  # request has to be passed this mocks it
        )


@pytest.mark.django_db
class TestRescheduleView:
    @pytest.fixture
    def create_user_details(db):
        user = UserFactory()
        provider_profile = ProviderProfileFactory(user=user)
        customer_profile = CustomerProfileFactory(user=user)
        notiications = NotificationPreferencesFactory(user=user)
        return user

    def test_unauthenticated_get(self, client):
        appointment = AppointmentFactory(status="accepted")
        response = client.get(
            reverse("reschedule", kwargs={"appointment_id": appointment.id}),
            follow=True,
        )
        assert response.status_code == 200
        redirection = f"/login/?next=/reschedule/{appointment.id}/"
        assert (redirection, 302) in response.redirect_chain

    def test_authenticated_get(self, client, create_user_details):
        user = create_user_details
        client.force_login(user)
        appointment = AppointmentFactory(customer=user, status="accepted")
        response = client.get(
            reverse("reschedule", kwargs={"appointment_id": appointment.id})
        )
        assert response.status_code == 200
        template_names = [t.name for t in response.templates]
        assert "customer/reschedule.html" in template_names

    def test_authenticated_post(self, client, create_user_details):
        user = create_user_details
        client.force_login(user)
        appointment = AppointmentFactory(customer=user, status="accepted")
        response = client.post(
            reverse("reschedule", kwargs={"appointment_id": appointment.id}),
            data={"checkschedule": "lalalala"},
            follow=True,
        )
        assert response.status_code == 200

        redirection = reverse(
            "schedule", kwargs={"providerID": appointment.provider.providerprofile.id}
        )
        assert (redirection, 302) in response.redirect_chain


@pytest.mark.django_db
class TestBookingHistoryView:
    @pytest.fixture
    def create_user_details(db):
        user = UserFactory()
        provider_profile = ProviderProfileFactory(user=user)
        customer_profile = CustomerProfileFactory(user=user)
        notiications = NotificationPreferencesFactory(user=user)
        return user

    def test_unauthenticated_get(self, client):
        response = client.get(reverse("booking_history"), follow=True)
        assert response.status_code == 200
        redirection = "/accounts/login/?next=/booking_history/"
        assert (redirection, 302) in response.redirect_chain

    @pytest.mark.parametrize(
        "status",
        [
            ("pending"),
            ("cancelled"),
            ("rejected"),
            ("rescheduled"),
            ("completed"),
            ("accepted"),
        ],
    )
    def test_authenticated_get(self, client, create_user_details, status):
        user = create_user_details
        appointment = AppointmentFactory(customer=user, status=status)
        client.force_login(user)
        response = client.get(reverse("booking_history"))
        assert response.status_code == 200
        template_names = [t.name for t in response.templates]
        assert "customer/booking_history.html" in template_names

        assert "page_obj" in response.context
        assert appointment in response.context["page_obj"]
