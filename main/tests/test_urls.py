import pytest
from django.urls import resolve, reverse

from main import views


def test_home_url_resolves():
    assert resolve(reverse("home")).func == views.home


def test_redirectiondashboard_url_resolves():
    assert resolve(reverse("redirectiondashboard")).func == views.redirectiondashboard


def test_profile_creation_url_resolves():
    assert resolve(reverse("profile_creation")).func == views.profile_creation


def test_connect_calendar_url_resolves():
    assert resolve(reverse("connect_to_calendar")).func == views.connect_to_calendar


def test_connect_google_url_resolves():
    assert resolve(reverse("connect_google")).func == views.connect_google


def test_oauth2callback_url_resolves():
    assert resolve(reverse("oauth2callback")).func == views.oauth2callback


def test_cancellation_policy_url_resolves():
    assert resolve(reverse("cancellation_policy")).func == views.cancellation_policy


def test_view_customer_profile_url_resolves():
    match = resolve(reverse("view_customer_profile", kwargs={"userID": 1}))
    assert match.func == views.view_customer_profile


def test_view_provider_profile_url_resolves():
    match = resolve(reverse("view_provider_profile", kwargs={"userID": 1}))
    assert match.func == views.view_provider_profile


def test_create_customer_profile_url_resolves():
    assert (
        resolve(reverse("create_customer_profile")).func
        == views.create_customer_profile
    )
