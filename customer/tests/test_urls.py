from django.urls import resolve
from customer import views


def test_customer_dashboard_url_resolves():
    assert resolve("/customer_dashboard/").func == views.customer_dashboard


def test_add_appointment_url_resolves():
    match = resolve("/add_appointment/1/")
    assert match.func == views.add_appointment


def test_view_providers_url_resolves():
    assert resolve("/view_providers/").func == views.view_providers


def test_schedule_url_resolves():
    match = resolve("/schedule/1/")
    assert match.func == views.schedule


def test_view_appointments_url_resolves():
    assert resolve("/view_appointments/").func == views.view_appointments


def test_reschedule_url_resolves():
    match = resolve("/reschedule/42/")
    assert match.func == views.reschedule


def test_booking_history_url_resolves():
    assert resolve("/booking_history/").func == views.booking_history
