from datetime import date, time

import pytest
from django.core.exceptions import ValidationError

from provider.forms import AvailabilityForm


@pytest.mark.django_db
class TestAvailabilityForm:
    BASE_DATA = {
        "cause": "Busyyy",
        "start_date": date(2025, 7, 29),
        "end_date": date(2025, 7, 29),  # same day
        "start_time": time(10, 0),  # 10:00 AM
        "end_time": time(12, 0),  # 12:00 PM
    }

    def test_availability_form_valid(self):
        data = self.BASE_DATA.copy()
        form = AvailabilityForm(data=data)
        assert form.is_valid()

    @pytest.mark.parametrize(
        "key,value",
        [
            ("start_date", date(2025, 8, 11)),
            ("end_date", date(2025, 7, 22)),
            ("start_time", time(17, 0)),
            ("end_time", time(8, 0)),
        ],
    )
    def test_availability_form_invalid(self, key, value):
        data = self.BASE_DATA.copy()
        data[key] = value
        form = AvailabilityForm(data=data)
        assert not form.is_valid()
