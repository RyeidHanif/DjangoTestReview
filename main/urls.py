from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("redirectiondashboard/", views.redirectiondashboard, name="redirectiondashboard"),
    path("create_profile/<str:n>", views.profile_creation, name="profile_creation"),
]
