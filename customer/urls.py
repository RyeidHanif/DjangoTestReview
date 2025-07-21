from django.urls import path 
from . import views


urlpatterns = [
    path("customerdashboard/", views.customerdashboard, name= "customerdashboard")
]