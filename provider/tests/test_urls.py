import pytest
from django.urls import resolve, reverse

from provider import views


@pytest.mark.django_db
def test_provider_dashboard_url():
    assert resolve(reverse("provider_dashboard")).func == views.provider_dashboard


@pytest.mark.django_db
def test_view_my_appointments_url():
    assert resolve(reverse("view_my_appointments")).func == views.view_my_appointments


@pytest.mark.django_db
def test_view_pending_appointments_url():
    assert (
        resolve(reverse("view_pending_appointments")).func
        == views.view_pending_appointments
    )


@pytest.mark.django_db
def test_view_analytics_url():
    assert resolve(reverse("view_analytics")).func == views.view_analytics


@pytest.mark.django_db
def test_my_availability_url():
    assert resolve(reverse("my_availability")).func == views.my_availability
