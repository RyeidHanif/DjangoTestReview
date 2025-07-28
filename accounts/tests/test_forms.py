import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from accounts.forms import (ChangeNotificationPreferencesForm,
                            ProfilePhotoForm, SignUpForm)

from .factories import ProviderProfileFactory


@pytest.mark.django_db
class TestSignUpForm:

    BASE_DATA = {
        "username": "testuser",
        "email": "test@example.com",
        "password1": "SuperSecure123",
        "password2": "SuperSecure123",
        "phone_number": "1234567890",
    }

    def test_signup_form_valid(self):
        form = SignUpForm(data=self.BASE_DATA)
        assert form.is_valid()

    @pytest.mark.parametrize(
        "field, value",
        [
            ("username", ""),
            ("email", "whywouldthisbeanemail"),
            ("password2", "matata"),
            ("phone_number", ""),
        ],
    )
    def test_signup_form_invalid(self, field, value):
        data = self.BASE_DATA.copy()
        data[field] = value
        form = SignUpForm(data=data)
        assert not form.is_valid()
        assert field in form.errors


@pytest.mark.django_db
class TestChangeNotificationPreferencesForm:
    @pytest.mark.parametrize(
        "pref",
        [
            ("all"),
            ("reminders"),
            ("none"),
        ],
    )
    def test_form_valid(self, pref):
        data = {"preferences": pref}
        form = ChangeNotificationPreferencesForm(data=data)
        assert form.is_valid()


@pytest.mark.django_db
class TestProfilePhotoForm:
    def test_profile_photo_form_valid(self):
        provider = ProviderProfileFactory()
        # 1. Create an in-memory image file
        image_io = io.BytesIO()  # Memory buffer to hold bytes (like a fake file)
        image = Image.new(
            "RGB", (100, 100), color="red"
        )  # Generate a red 100x100 image
        image.save(image_io, format="JPEG")  # Save image data into the buffer as JPEG
        image_io.seek(0)  # Reset buffer pointer to the start (important!)

        # 2. Wrap this bytes data as an UploadedFile (mimics file upload)
        uploaded_file = SimpleUploadedFile(
            "test_image.jpg",  # filename for the form
            image_io.read(),  # actual image bytes
            content_type="image/jpeg",  # MIME type for the upload
        )

        # 3. Setup form data (empty here because form only has image)
        form_data = {}
        form_files = {"profile_photo": uploaded_file}  # files dict for file uploads

        # 4. Instantiate form with data & files
        form = ProfilePhotoForm(data=form_data, files=form_files, instance=provider)

        # 5. Check validation: is the uploaded image accepted?
        assert form.is_valid()

        # 6. Save form and get model instance
        instance = form.save()

        # 7. Assert the image was saved with the right filename
        assert instance.profile_photo.name.startswith("test_image")
        assert instance.profile_photo.name.endswith(".jpg")
