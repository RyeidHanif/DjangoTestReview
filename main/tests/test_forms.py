import pytest

from main.forms import ProviderForm

from .factories import ProviderProfile


@pytest.mark.django_db
class TestProviderForm:
    BASE_DATA = {
        "service_category": "doctor",
        "service_name": "chingchong",
        "pricing_model": "fixed",
        "duration_mins": "60",
        "start_time": "09:00",
        "end_time": "17:30",
        "rate": "3000",
        "buffer": "5",
        "profile_photo": None,
    }

    def test_provider_form_valid(self):
        data = self.BASE_DATA.copy()
        form = ProviderForm(data=data)
        assert form.is_valid()

    @pytest.mark.parametrize(
        "key,value",
        [
            ("service_category", "banana"),
            (
                "service_name",
                "shalalalaalalalalalaalalufdhhhhhhhhhiiighjfvnjkndjhfffdhhjdhdjhvjhfhvhjfvgfjhvfjhbvhjbfhjbjhjkhjvbhjvbhvbhjdhjjgfhjgjf",
            ),
            ("pricing_model", "opensource"),
            ("duration_mins", ""),
            ("start_time", "2900"),
            ("end_time", "3900"),
            ("rate", ""),
            ("buffer", ""),
            ("end_time", "8:00"),
        ],
    )
    def test_invalid_form_data(self, key, value):
        data = self.BASE_DATA.copy()
        data[key] = value
        form = ProviderForm(data=data)
        assert not form.is_valid()
