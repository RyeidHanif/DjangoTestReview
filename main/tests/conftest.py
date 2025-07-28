import pytest
from django.contrib.auth.models import User
from .factories import UserFactory

@pytest.fixture 
def create_normal_user(db):
    random_user = UserFactory()
    return random_user
