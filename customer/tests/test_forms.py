from datetime import date, timedelta

import pytest
from django.core.exceptions import ValidationError

from customer.forms import AppointmentRecurrenceForm


@pytest.mark.parametrize(
    "recurrence, until_date, appointment_date, should_be_valid",
    [
        ("NONE", None, date.today(), True),
        ("DAILY", date.today() + timedelta(days=1), date.today(), True),
        ("WEEKLY", date.today() - timedelta(days=1), date.today(), False),  # invalid
        (None, None, date.today(), True),
    ],
)
def test_appointment_recurrence_form_validation(
    recurrence, until_date, appointment_date, should_be_valid
):
    data = {
        "recurrence": recurrence,
        "until_date": until_date,
    }

    form = AppointmentRecurrenceForm(data=data, appointment_date=appointment_date)

    if should_be_valid:
        assert form.is_valid()
    else:
        assert not form.is_valid()
        assert "until_date" in form.errors
        assert "cannot be before the appointment date" in form.errors["until_date"][0]
