import pytest
from django.urls import resolve

from accounts import views


def test_signup_url_resolves():
    assert resolve("/signup/").func == views.signup


def test_activate_url_resolves():
    match = resolve("/activate/uidb64sample/token123")
    assert match.func == views.activate
    assert match.kwargs["uidb64"] == "uidb64sample"
    assert match.kwargs["token"] == "token123"


def test_password_change_url_resolves():
    assert resolve("/password_change").func == views.password_change


def test_user_profile_url_resolves():
    assert resolve("/user_profile/").func == views.user_profile


def test_modify_profile_url_resolves():
    assert resolve("/modify_profile/").func == views.modify_profile


def test_delete_account_url_resolves():
    assert resolve("/delete_account/").func == views.delete_account
