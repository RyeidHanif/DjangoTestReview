from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import User


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Allow the application to sync properly with social accounts

    by default , django AllAuth does not sync with already present accounts and their email addresses
    Hence the users directly logging in and those using google SSO would have problems in accessing their accounts
    with the other option .
    This is required to make sure that the same email is used only once per account and it can be cross references to that account
    by django all-auth
    """

    def pre_social_login(self, request, sociallogin):
        # If user is already logged in, no action
        if request.user.is_authenticated:
            return

        # Try to find user with the same email address as the social account
        email = sociallogin.account.extra_data.get("email")
        if email:
            try:
                user = User.objects.get(email=email)
                sociallogin.connect(request, user)
            except User.DoesNotExist:
                pass
