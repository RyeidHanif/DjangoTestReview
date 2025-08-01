from datetime import datetime
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
class TestRedirectionDashboard:

    def test_unauthenticated_get(self, client):
        response = client.get(reverse("redirectiondashboard"), follow=True)
        assert response.status_code == 200
        redirection = "/login/?next=/redirectiondashboard/"
        assert (redirection, 302) in response.redirect_chain

    @pytest.mark.parametrize(
        "has_provider, has_customer, expected_redirect",
        [
            (True, True, "connect_to_calendar"),
            (True, False, "connect_to_calendar"),
            (False, True, "customer_dashboard"),
            (False, False, "create_customer_profile"),
        ],
    )
    def test_authenticated_redirection(
        self, client, db, has_provider, has_customer, expected_redirect
    ):
        user = UserFactory()
        if has_provider:
            ProviderProfileFactory(user=user)
        if has_customer:
            CustomerProfileFactory(user=user)

        client.force_login(user)
        response = client.get(reverse("redirectiondashboard"), follow=True)
        assert response.status_code == 200
        assert (reverse(expected_redirect), 302) in response.redirect_chain


@pytest.mark.django_db
class TestProfileCreation:
    data = {
        "service_category": "doctor",
        "service_name": "Basic Trim",
        "pricing_model": "hourly",  # or 'fixed'
        "duration_mins": 45,
        "start_time": "10:00",
        "end_time": "18:00",
        "rate": 1500,
        "buffer": 15,
        "profile_photo": "",
    }

    @pytest.fixture
    def create_user(db):
        user = UserFactory()
        customer_profile = CustomerProfileFactory(user=user)
        return user

    def test_unauthenticated_get(self, client, create_user):
        response = client.get(reverse("profile_creation"), follow=True)
        assert response.status_code == 200
        redirection = reverse("login") + "?next=/create_profile/"
        assert (redirection, 302) in response.redirect_chain

    def test_authenticated_get(self, client, create_user):
        user = create_user
        client.force_login(user)
        response = client.get(reverse("profile_creation"))
        assert response.status_code == 200
        template_names = [t.name for t in response.templates]
        assert "main/profile_creation.html" in template_names
        assert "form" in response.context

    def test_provider_profile_already_created_post(self, client, create_user):
        user = create_user
        provider_profile = ProviderProfileFactory(user=user)

        client.force_login(user)
        response = client.post(reverse("profile_creation"), data=self.data, follow=True)

        assert response.status_code == 200
        redirection = reverse("provider_dashboard")
        assert (redirection, 302) in response.redirect_chain

    def test_provider_profile_not_created_post(self, client, create_user):
        user = create_user
        client.force_login(user)
        response = client.post(reverse("profile_creation"), data=self.data, follow=True)
        assert response.status_code == 200
        redirection = reverse("redirectiondashboard")
        assert (redirection, 302) in response.redirect_chain

        assert user.providerprofile.phone_number == user.customerprofile.phone_number


@pytest.mark.django_db
class TestConnectToCalendar:
    @pytest.fixture
    def create_user(db):
        user = UserFactory()
        provider_profile = ProviderProfileFactory(user=user)
        customer_profile = CustomerProfileFactory(user=user)
        return user

    def test_unauthenticated_get(self, client):
        response = client.get(reverse("connect_to_calendar"), follow=True)
        assert response.status_code == 200
        redirection = reverse("login") + "?next=/connect_calendar"
        assert (redirection, 302) in response.redirect_chain

    def test_authenticated_get_calendar_connected(self, client, create_user):
        user = create_user
        user.providerprofile.google_calendar_connected = True
        user.providerprofile.save()
        client.force_login(user)
        response = client.get(reverse("connect_to_calendar"), follow=True)
        assert response.status_code == 200
        redirection = reverse("provider_dashboard")
        assert (redirection, 302) in response.redirect_chain

    @patch("main.views.redirect")
    def test_authenticated_calendar_not_connected_post(
        self, mock_redirect, client, create_user
    ):
        user = create_user
        client.force_login(user)

        # Setup mock to return a real HttpResponseRedirect
        redirect_url = reverse("connect_google")
        mock_redirect.return_value = HttpResponseRedirect(redirect_url)

        response = client.post(reverse("connect_to_calendar"))

        # This is now real so status_code and redirect_chain work
        assert response.status_code == 302
        mock_redirect.assert_called_with("connect_google")

    def test_authenticated_get_calendar_not_connected(self, client, create_user):
        user = create_user
        client.force_login(user)
        response = client.get(reverse("connect_to_calendar"))
        assert response.status_code == 200
        template_names = [t.name for t in response.templates]
        assert "main/connect_to_calendar.html" in template_names


@pytest.mark.django_db
class TestAdminDashboardView:

    @pytest.fixture
    def create_normal_user(db):
        user = UserFactory()
        ProviderProfileFactory(user=user)
        CustomerProfileFactory(user=user)
        return user  # <-- Return user

    @pytest.fixture
    def create_admin_user(db):
        user = UserFactory(is_staff=True, is_superuser=True)
        ProviderProfileFactory(user=user)
        CustomerProfileFactory(user=user)
        return user  # <-- Return user

    def test_unauthenticated_get(self, client):
        response = client.get(reverse("admin-analytics"), follow=True)
        assert response.status_code == 200
        # Django admin login URL includes trailing slash and "admin/login/"
        redirection = "/admin/login/?next=/admin/analytics/"
        assert (redirection, 302) in response.redirect_chain

    def test_non_admin_get(self, client, create_normal_user):
        user = create_normal_user
        client.force_login(user)
        response = client.get(reverse("admin-analytics"), follow=True)
        assert response.status_code == 200
        # Non-staff users accessing Django admin are redirected to login page
        redirection = "/admin/login/?next=/admin/analytics/"
        assert (redirection, 302) in response.redirect_chain

    @pytest.mark.parametrize(
        "item",
        [
            "revenue",
            "myrevenue",
            "statuses",
            "all_appointments",
            "all_providers",
            "all_customers",
            "total_appointments",
            "page_obj",
            "provider_dict",
            "categories",
        ],
    )
    def test_admin_get(self, client, create_admin_user, item):
        user = create_admin_user
        client.force_login(user)
        response = client.get(reverse("admin-analytics"))
        assert response.status_code == 200
        template_names = [t.name for t in response.templates]
        assert "main/admin_dashboard.html" in template_names
        assert item in response.context

    def test_admin_post_toggle_active(
        self, client, create_admin_user, create_normal_user
    ):
        user = create_admin_user
        other_user = create_normal_user
        assert other_user.is_active == True

        client.force_login(user)
        response = client.post(
            reverse("admin-analytics"), data={"toggle_active": other_user.id}
        )
        assert response.status_code == 200
        check_other_user = User.objects.get(id=other_user.id)
        assert check_other_user.is_active == False

    def test_admin_post_delete_user(
        self, client, create_admin_user, create_normal_user
    ):
        user = create_admin_user
        other_user = create_normal_user

        client.force_login(user)
        response = client.post(
            reverse("admin-analytics"), data={"delete": other_user.id}
        )
        assert response.status_code == 200

        with pytest.raises(User.DoesNotExist):
            User.objects.get(id=other_user.id)


@pytest.mark.django_db
class TestViewCustomerProfile:
    @pytest.fixture
    def create_normal_user(db):
        user = UserFactory()
        ProviderProfileFactory(user=user)
        CustomerProfileFactory(user=user)
        return user  # <-- Return user

    @pytest.fixture
    def create_admin_user(db):
        user = UserFactory(is_staff=True, is_superuser=True)
        ProviderProfileFactory(user=user)
        CustomerProfileFactory(user=user)
        return user  # <-- Return user

    def test_unauthenticated_get(self, client, create_normal_user):
        other_user = create_normal_user
        response = client.get(
            reverse("view_customer_profile", kwargs={"userID": other_user.id}),
            follow=True,
        )
        assert response.status_code == 200
        # Django admin login URL includes trailing slash and "admin/login/"
        redirection = f"/admin/login/?next=/view_customer_profile/{other_user.id}"
        assert (redirection, 302) in response.redirect_chain

    def test_non_admin_get(self, client, create_normal_user):
        other_user = create_normal_user
        user = create_normal_user
        client.force_login(user)
        response = client.get(
            reverse("view_customer_profile", kwargs={"userID": other_user.id}),
            follow=True,
        )
        assert response.status_code == 200
        redirection = f"/admin/login/?next=/view_customer_profile/{other_user.id}"
        assert (redirection, 302) in response.redirect_chain

    def test_authenticated_admin_get(
        self, client, create_admin_user, create_normal_user
    ):
        other_user = create_normal_user
        user = create_admin_user
        client.force_login(user)
        response = client.get(
            reverse("view_customer_profile", kwargs={"userID": other_user.id})
        )
        assert response.status_code == 200
        template_names = [t.name for t in response.templates]
        assert "main/view_customer_profile.html" in template_names
        assert "user" in response.context
        assert "user_customer_profile" in response.context
        assert "appointments_customer" in response.context


@pytest.mark.django_db
class TestViewProviderProfile:
    @pytest.fixture
    def create_normal_user(db):
        user = UserFactory()
        ProviderProfileFactory(user=user)
        CustomerProfileFactory(user=user)
        return user  # <-- Return user

    @pytest.fixture
    def create_admin_user(db):
        user = UserFactory(is_staff=True, is_superuser=True)
        ProviderProfileFactory(user=user)
        CustomerProfileFactory(user=user)
        return user  # <-- Return user

    def test_unauthenticated_get(self, client, create_normal_user):
        other_user = create_normal_user
        response = client.get(
            reverse("view_provider_profile", kwargs={"userID": other_user.id}),
            follow=True,
        )
        assert response.status_code == 200
        # Django admin login URL includes trailing slash and "admin/login/"
        redirection = f"/admin/login/?next=/view_provider_profile/{other_user.id}"
        assert (redirection, 302) in response.redirect_chain

    def test_non_admin_get(self, client, create_normal_user):
        other_user = create_normal_user
        user = create_normal_user
        client.force_login(user)
        response = client.get(
            reverse("view_provider_profile", kwargs={"userID": other_user.id}),
            follow=True,
        )
        assert response.status_code == 200
        redirection = f"/admin/login/?next=/view_provider_profile/{other_user.id}"
        assert (redirection, 302) in response.redirect_chain

    def test_authenticated_admin_get(
        self, client, create_admin_user, create_normal_user
    ):
        other_user = create_normal_user
        user = create_admin_user
        client.force_login(user)
        response = client.get(
            reverse("view_provider_profile", kwargs={"userID": other_user.id})
        )
        assert response.status_code == 200
        template_names = [t.name for t in response.templates]
        assert "main/view_provider_profile.html" in template_names
        assert "user" in response.context
        assert "user_provider_profile" in response.context
        assert "appointments_provider" in response.context


@pytest.mark.django_db
class TestCreateCustomerProfileView:
    @pytest.fixture
    def create_user(db):
        user = UserFactory()
        customer_profile = CustomerProfileFactory(user=user)
        provider_profile = ProviderProfileFactory(user=user)
        return user

    def test_authenticated_get(self, client, create_user):
        user = create_user
        client.force_login(user)
        response = client.get(reverse("create_customer_profile"))
        assert response.status_code == 200
        template_names = [t.name for t in response.templates]
        assert "main/create_customer_profile.html" in template_names
        assert "form" in response.context


@pytest.mark.django_db
class TestConnectGoogle:

    @patch("main.views.GoogleCalendarClient")
    def test_connect_google_success(self, mock_client, client):
        mock_instance = mock_client.return_value
        mock_instance.create_auth_url.return_value = "http://fake-auth-url.com"

        response = client.get(reverse("connect_google"))

        assert response.status_code == 302
        assert response.url == "http://fake-auth-url.com"
        mock_instance.create_auth_url.assert_called_once()

    @patch("main.views.GoogleCalendarClient")
    def test_connect_google_failure(self, mock_client, client):
        mock_instance = mock_client.return_value
        mock_instance.create_auth_url.side_effect = Exception("Boom")

        response = client.get(reverse("connect_google"))

        assert response.status_code == 400


@pytest.mark.django_db
class TestOAuth2Callback:
    @pytest.fixture
    def create_provider_user(db):
        user = UserFactory()
        ProviderProfileFactory(user=user)
        return user

    @patch("main.views.GoogleCalendarClient")
    def test_oauth2callback_success(self, mock_client, client, create_provider_user):
        user = create_provider_user
        client.force_login(user)
        mock_instance = mock_client.return_value

        response = client.get(reverse("oauth2callback"))

        assert response.status_code == 302
        assert response.url == reverse("provider_dashboard")
        mock_instance.google_calendar_callback.assert_called_once()

    @patch("main.views.GoogleCalendarClient")
    def test_oauth2callback_failure(self, mock_client, client, create_provider_user):
        user = create_provider_user
        client.force_login(user)
        mock_instance = mock_client.return_value
        mock_instance.google_calendar_callback.side_effect = Exception(
            "Callback failed"
        )

        response = client.get(reverse("oauth2callback"))

        assert response.status_code == 400
