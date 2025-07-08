from django.db import models

from django.contrib.auth.models import User


# Create your models here.


class Post(models.Model):
    name = models.CharField(max_length=20)
    content = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
