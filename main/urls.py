from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("create_profile/<str:n>", views.profile_creation, name="profile_creation"),
]
