import pytest 
from .factories import UserFactory , ProviderProfileFactory , CustomerProfileFactory , NotificationPreferencesFactory 
from django.urls import reverse
from main.models import User, NotificationPreferences, ProviderProfile
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from accounts.tokens import account_activation_token


@pytest.mark.django_db
class TestSignUpView:

    def test_get_returns_correct_data(self , client ):
        response = client.get(reverse("signup"))
        assert response.status_code == 200 
        assert "form" in response.context 
        template_names = [t.name for t in response.templates]
        assert "accounts/signup.html" in template_names
    
    def test_post_returns_correct(self , client):

        response = client.post(reverse("signup"), {"username": "lalo" , "email" : "lalo@gmail.com" , "password1": "salamanca456789234" , "password2": "salamanca456789234" , "phone_number":"50555505"}, follow=True)



        form = response.context.get("form")
        if form:
         print(form.errors)
        assert response.status_code == 200  # Final response after redirect
        assert response.redirect_chain == [ (reverse("home"), 302) ]  #chain . 302 is what signup does basically because of follow=True
        user = User.objects.get(username="lalo")
        assert user.email == "lalo@gmail.com"
        assert user.is_active is False 
    
#not testing an invalid post here because it is only a form and that is done in test_forms.py which works perfetly fine 


@pytest.mark.django_db
class TestUserProfileView:
   
    @pytest.fixture
    def create_user_details(db):
      user = UserFactory(username="lalosalamanca")
      provider_profile = ProviderProfileFactory(user=user)
      customer_profile = CustomerProfileFactory(user=user)
      notification_preferences = NotificationPreferencesFactory(user=user)
      return user
      
   
    def test_get_context(self, client, create_user_details):
        user = create_user_details
        client.force_login(user)

        response = client.get(reverse("user_profile"))
        
        
        assert "me" in response.context
        assert "my_provider" in response.context
        assert "my_customer" in response.context
        assert "form" in response.context
        assert "change_profile_form" in response.context


      
    
    def test_get_status(self, client, create_user_details):
        user = create_user_details


        client.login(username="lalosalamanca", password="password123", backend='django.contrib.auth.backends.ModelBackend')

       

        print(f"Login: {user.username}, is_authenticated: {user.is_authenticated}")
        response = client.get(reverse("user_profile"))

        
        assert response.status_code == 200
        assert "accounts/user_profile.html" in [t.name for t in response.templates]
        assert response.context["me"].id == user.id

    def test_non_logged_in_user(self , client ):
        response = client.get(reverse("user_profile"), follow=True)
        url = reverse("user_profile")
        assert response.status_code == 200 
        assert ("/login/?next=" + url, 302) in response.redirect_chain
    
    def test_post_change_notifications(self , client , create_user_details):
        user = create_user_details
        assert user.notification_settings.preferences == "all"
        client.force_login(user)
        response = client.post(reverse("user_profile"), {"preferences": "none", "changenot": "1"})

        assert response.status_code == 200
        user.refresh_from_db()
        user.notification_settings.refresh_from_db()

        assert user.notification_settings.preferences == "none"

        pref = NotificationPreferences.objects.get(user=user)
        assert pref.preferences == "none"

    def test_post_modify_profile(self, client, create_user_details):
        user = create_user_details
        client.force_login(user)
        response = client.post(reverse("user_profile"),{"modify_profile": "1"}, follow=True)
        assert response.status_code == 200
        assert response.redirect_chain == [ (reverse("modify_profile"), 302) ]
    

    def test_post_delete_account(self, client , create_user_details):
        user=create_user_details
        client.force_login(user)
        response = client.post(reverse("user_profile"), {"delete_account": "1"}, follow = True)
        assert response.status_code == 200 
        assert response.redirect_chain == [(reverse("delete_account"), 302)]
    
    def test_post_disconnect_calendar(self, client , create_user_details):
        user=UserFactory()
        provider_profile = ProviderProfileFactory(user = user ,google_calendar_connected=True)

        client.force_login(user)
        response = client.post(reverse("user_profile"), {"disconnect": "1"})
        connected = ProviderProfile.objects.get(user=user).google_calendar_connected
        assert not connected 
        assert response.status_code == 302

    def test_post_change_pfp(self, client , create_user_details):
        user = create_user_details
        client.force_login(user)
        response = client.post(reverse("user_profile"), {"change_pfp": 1})
        assert response.status_code == 200 

  


    
@pytest.mark.django_db
class TestModifyProfileView:

    @pytest.fixture
    def create_user_details(db):
        user = UserFactory(username="lalosalamanca")
        provider_profile = ProviderProfileFactory(user=user)
        customer_profile = CustomerProfileFactory(user=user)
        notification_preferences = NotificationPreferencesFactory(user=user)
        return user
    

    def test_get_data(self , client , create_user_details):
        user=create_user_details
        client.force_login(user)
        response = client.get(reverse("modify_profile"))
        assert response.status_code == 200 
        template_names = [t.name for t in response.templates]
        assert "accounts/modify_profile.html" in template_names 
        assert "form" in response.context
    


@pytest.mark.django_db
class TestDeleteAccountView:
    @pytest.fixture
    def create_user_details(db):
        user = UserFactory(username="lalosalamanca")
        provider_profile = ProviderProfileFactory(user=user)
        customer_profile = CustomerProfileFactory(user=user)
        notification_preferences = NotificationPreferencesFactory(user=user)
        return user

    def test_get_data(self , client , create_user_details):
        user= create_user_details
        client.force_login(user)
        response = client.get(reverse("delete_account"))
        assert response.status_code == 200 
        template_names = [t.name for t in response.templates]
        assert "accounts/delete_account.html" in template_names 

    
    def test_post_delete(self, client, create_user_details):
        user = create_user_details
        client.force_login(user)
        response = client.post(reverse("delete_account"))
        assert response.status_code == 302
        with pytest.raises(User.DoesNotExist):
            User.objects.get(id=user.id)
        
    

@pytest.mark.django_db
class TestPasswordChangeView:
    @pytest.fixture
    def create_user_details(db):
        user = UserFactory(username="lalosalamanca")
        provider_profile = ProviderProfileFactory(user=user)
        customer_profile = CustomerProfileFactory(user=user)
        notification_preferences = NotificationPreferencesFactory(user=user)
        return user


    def test_password_change_success(self , client , create_user_details):
        user = create_user_details
        client.force_login(user)

        response = client.post(
            reverse("password_change"),
            {
                "new_password1": "newsecurepass123",
                "new_password2": "newsecurepass123",
            },
        )

        assert response.status_code == 302  # redirected to login
        user.refresh_from_db()
        assert user.check_password("newsecurepass123")


def test_activation_success(client, db):
    user = UserFactory(is_active=False)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = account_activation_token.make_token(user)
    
    response = client.get(reverse("activate", kwargs={"uidb64": uid, "token": token}))

    user.refresh_from_db()
    assert user.is_active
    assert NotificationPreferences.objects.filter(user=user).exists()
    assert response.status_code == 302
    assert response.url == reverse("customer_dashboard")