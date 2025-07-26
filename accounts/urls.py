# from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("activate/<uidb64>/<token>", views.activate, name="activate"),
    path("password_change", views.password_change, name="password_change"),
    path("use_profile/", views.user_profile, name="user_profile"),
    path("modify_profile/", views.modify_profile, name="modify_profile"),
    path("delete_account/", views.delete_account, name="delete_account"),
]
