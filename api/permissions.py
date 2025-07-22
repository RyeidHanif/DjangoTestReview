from rest_framework.permissions import BasePermission


class CustomHasProviderProfile(BasePermission):
    def has_permission(self, request, view):
        return hasattr(request.user, "providerprofile")
