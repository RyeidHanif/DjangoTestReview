from rest_framework.permissions import BasePermission


class CustomHasProviderProfile(BasePermission):
    '''
    Cusom Permission created to be used in the APIViews since many views must only be accessed by someone 
    who has a provider profile 
    '''
    def has_permission(self, request, view):
        return hasattr(request.user, "providerprofile")
