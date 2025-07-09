from django.db import models
from  django.contrib.auth.models import AbstractUser
import uuid
# Create your models here.

class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phoneno = models.CharField(max_length=13)
    email = models.EmailField(unique = True)

    USER_TYPE_OPTIOSN = (
        ('customer', 'Customer'),
        ('provider', 'Provider')
    )
 
    user_type = models.CharField(max_length=10 , choices = USER_TYPE_OPTIOSN, default ="customer")

    REQUIRED_FIELDS =[ "email", "user_type", "phoneno",]