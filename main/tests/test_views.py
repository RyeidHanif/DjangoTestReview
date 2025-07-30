import pytest
from .factories import UserFactory , ProviderProfileFactory , CustomerProfileFactory , AppointmentFactory , NotificationPreferencesFactory
from main.models import ProviderProfile , CustomerProfile , Appointment , NotificationPreferences

from django.urls import reverse
from django.contrib.auth.models import User
      
from unittest.mock import patch, MagicMock, ANY 
from django.contrib.messages import get_messages


from django.utils import timezone 
from datetime import datetime



@pytest.mark.django_db
class TestRedirectionDashboard:

    

    def test_unauthenticated_get(self , client):
        response = client.get(reverse("redirectiondashboard"), follow=True)
        assert response.status_code == 200
        redirection = "/login/?next=/redirectiondashboard/"
        assert (redirection , 302) in response.redirect_chain
    
    @pytest.mark.parametrize(
        "has_provider, has_customer, expected_redirect",
        [
            (True, True, "connect_to_calendar"),
            (True, False, "connect_to_calendar"),
            (False, True, "customer_dashboard"),
            (False, False, "create_customer_profile"),
        ]
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


    


    