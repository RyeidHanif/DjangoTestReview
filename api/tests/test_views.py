import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from .factories import UserFactory, CustomerProfileFactory , ProviderProfileFactory, AppointmentFactory
from unittest.mock import ANY, MagicMock, patch
from datetime import datetime , timedelta
from django.utils.timezone import now , localtime , localdate , get_current_timezone
@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user(db):
    user = UserFactory()
    provider_profile = ProviderProfileFactory(user=user, google_calendar_connected=True)
    customer_profile = CustomerProfileFactory(user=user)
    return user

@pytest.fixture
def access_token(api_client, user):
    url = reverse("token_obtain_pair")
    response = api_client.post(
        url,
        {"username": user.username, "password": "password123"},
        format="json"
    )
    return response.data["access"]

@pytest.mark.django_db
class TestSignUp:
    def test_successful_signup(self, api_client):
        url = reverse("api_register")
        data = {
            "username": "Beifong",
            "password": "analysis130",
            "email": "beifong@gmail.com"
        }
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["username"] == "Beifong"
        assert response.data["email"] == "beifong@gmail.com"

    def test_invalid_signup(self, api_client):
        url = reverse("api_register")
        data = {"username": "jam"}
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.data
        assert response.data["password"][0] == "This field is required."

@pytest.mark.django_db
class TestWelcomeView:
    def test_welcome_authenticated(self, api_client, access_token, user):
        url = reverse("api_welcome")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert user.username in response.data["message"]

    def test_welcome_unauthenticated(self, api_client):
        url = reverse("api_welcome")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
class TestUserProfileView:
    def test_unauthenticated_get(self, api_client):
        url = reverse("api_user_profile")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    @pytest.mark.parametrize("item",[ 
        ("user"),
        ("phone_number"),
        ("service_category"),
        ("service_name"),
        ("pricing_model"),
        ("duration_mins"),
        ("start_time"),
        ("end_time"),
        ("rate"),
        ("buffer")
    ])
    def test_authenticated_get(self, api_client, access_token , item ):
        url = reverse("api_user_profile")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert item in response.data



@pytest.mark.django_db
class TestProviderAppointments:
    def test_unauthenticated_get(self, api_client):
        url = reverse("api_provider_appointments")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.parametrize("item",[ 
        ("provider"),
        ("customer"),
        ("date_start"),
        ("date_end"),
        ("date_added"),
        ("status"),
        ("total_price"),
        ("special_requests"),
        ("recurrence_frequency"),
        ("recurrence_until"),
    ])
    def test_authenticated_get(self, api_client, access_token, user, item):
        appointment = AppointmentFactory(provider=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = api_client.get(reverse("api_provider_appointments"))

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list) and len(response.data) > 0

        # Get the appointment object from inside the wrapper
        wrapped = response.data[0]
        assert "appointment" in wrapped
        inner_appointment = wrapped["appointment"]


        assert item in inner_appointment

        if item == "provider":
            assert inner_appointment["provider"]["username"] == user.username



@pytest.mark.django_db
class TestCustomerAppointmentsView:
    def test_unauthenticated_get(self, api_client):
        url = reverse("api_customer_appointments")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.parametrize("item",[ 
        ("provider"),
        ("customer"),
        ("date_start"),
        ("date_end"),
        ("date_added"),
        ("status"),
        ("total_price"),
        ("special_requests"),
        ("recurrence_frequency"),
        ("recurrence_until"),
    ])
    def test_authenticated_get(self, api_client, access_token, user, item):
        appointment = AppointmentFactory(customer=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = api_client.get(reverse("api_customer_appointments"))

        assert response.status_code == status.HTTP_200_OK
        wrapped = response.data[0]
        assert "appointment" in wrapped
        inner_appointment = wrapped["appointment"]


        assert item in inner_appointment

        if item == "customer":
            assert inner_appointment["customer"]["username"] == user.username



@pytest.mark.django_db
class TestApiProviderAvailability:
    @pytest.fixture
    def customer_only(db):
        customer = UserFactory()
        CustomerProfileFactory(user=customer)
        return customer
    
    def test_unauthenticated_get(self , api_client , user):
        url = reverse("api_provider_availability", kwargs={"providerID": user.id})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @patch("api.views.GoogleCalendarClient")
    def test_authenticated_get(self,mock_calendar_client ,  api_client ,access_token , user , customer_only):
        customer = customer_only
        provider = user 
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        mock_calendar_client.return_value.get_available_slots.return_value = [(now() , now() + timedelta(minutes=60))]
        url = reverse("api_provider_availability", kwargs={"providerID": provider.id})
        response = api_client.get(f"{url}?slot_range=1")
        assert response.status_code == status.HTTP_200_OK
        slots = response.data['Available slots'][0]
        assert 'start_date' in slots
        assert 'end_date' in slots 
        assert 'start_time' in slots
        assert 'end_time' in slots 
        assert 'timezone' in slots 






@pytest.mark.django_db
class TestApiProviderAnalyticsView:
    def test_unauthenticated_get(self , api_client):
        url = reverse("api_provider_analytics")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    

    def test_authenticated_get(self, api_client, access_token,  user ):
        for i in range(10):
            if i//2 == 0 :
                AppointmentFactory(provider=user,  date_start = now() + timedelta(hours=i), date_end = now()+ timedelta(hours=i) + timedelta(minutes=30))
            else :
                AppointmentFactory(provider=user,  date_start = now() - timedelta(hours=i), date_end = now() -timedelta(hours=i) + timedelta(minutes=30))
            
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        url = reverse("api_provider_analytics")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data["provider"] == user.username
        assert len(data["appointments"]) == 10


        first = data["appointments"][0]
        assert first["provider"]["username"] == user.username
        assert first["customer"]["username"] is not None
        assert first["status"] == "pending"
        assert first["total_price"] == 3000.0


        assert data["total_appointments"] == 10
        assert data["admin_revenue"] == 0.0
        assert data["statuses"]["pending"] == 10


        

@pytest.mark.django_db
class TestViewProviders:
    def test_unauthenticated_get(self , api_client):
        url = reverse("api_view_providers")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    

    def test_authenticated_get(self, api_client, access_token , user):
        url = reverse("api_view_providers")

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        for i in range(10):
            provider = UserFactory()
            ProviderProfileFactory(user=provider ,rate = 100 * i)
            CustomerProfileFactory(user=provider)

        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert len(data) == 10 
        provider_usernames = [item["provider"]["user"]["username"] for item in data]
        assert user.username  not in provider_usernames

        first = data[0]["provider"]

        assert first["user"]["username"] is not None 
        assert first["user"]["email"] is not None 
        assert first["rate"] == 0.0
        assert first["pricing_model"] == "fixed"
        assert first["start_time"] == "09:00:00"
        assert first["end_time"] == "17:00:00"







    


    
