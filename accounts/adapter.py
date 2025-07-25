from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import User



class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # If user is already logged in, no action
        if request.user.is_authenticated:
            return

        # Try to find user with the same email address as the social account
        email = sociallogin.account.extra_data.get('email')
        if email:
            try:
                user = User.objects.get(email=email)
                sociallogin.connect(request, user)
            except User.DoesNotExist:
                pass
