import pytest
from main.models import ProviderProfile, Appointment, NotificationPreferences
from .factories import ProviderProfileFactory, UserFactory, CustomerProfileFactory, AppointmentFactory ,NotificationPreferencesFactory
from django.core.exceptions import ValidationError
from django.utils.timezone import localtime , now , is_aware



@pytest.mark.django_db
class TestProviderProfile:
    def test_provider_profile_creation(self):
        profile = ProviderProfileFactory()
        assert profile.pk is not None 
        assert profile.user.is_active == True 
        assert profile.service_category == "doctor"
        assert profile.start_time.hour == 9
        assert profile.end_time.hour == 17
        assert profile.phone_number is not None 
    
    def test_provider_profile_str(self):
        profile = ProviderProfileFactory()
        assert str(profile) == f"provider profile of user {profile.user.username}"

    def test_null_fields(self):
        profile=ProviderProfileFactory()
        assert profile.google_access_token == None
        assert profile.google_refresh_token == None
        assert profile.google_token_expiry == None 
        assert profile.google_calendar_connected == False 
    
    @pytest.mark.django_db
    @pytest.mark.parametrize("service_category, should_raise", [
        ("doctor", False),
        ("consultant", False),
        ("therapist", False),
        ("counsellor", False),
        ("astronaaat", True),  # invalid category, expect ValidationError
    ])
    def test_service_category_validation(self, service_category, should_raise):
        profile = ProviderProfileFactory(service_category=service_category)
        if should_raise:
            with pytest.raises(ValidationError):
                profile.full_clean()
        else:
            profile.full_clean()  # should not raise
            profile.save()
            assert profile.pk is not None



    def test_inactive_user_not_shown(self):
        profile = ProviderProfileFactory(user__is_active = False )
        active_profiles = ProviderProfile.objects.all()
        assert profile not in active_profiles


        all_profiles = ProviderProfile.all_objects.all()
        assert profile in all_profiles 
        
     

        
        
@pytest.mark.django_db
class TestCustomerProfile:
    def test_customer_profile_creation(self):
        customer = CustomerProfileFactory() # implicitly does .create so goes to db 
        assert customer.pk is not None
        assert customer.user.is_active == True 
        assert customer.phone_number is not None 
    

    def test_customer_profile_str(self):
        customer = CustomerProfileFactory()
        assert str(customer) == f"customer profile of user {customer.user.username}"





@pytest.mark.django_db
class TestAppointment:
    def test_appointment_creation(self):
        appointment = AppointmentFactory()
        assert appointment.provider.pk is not None 
        assert appointment.customer.pk is not None 
        assert appointment.date_start is not None 
        assert appointment.date_end is not None 
        assert appointment.status == "pending"
        assert appointment.event_id == None 
        assert appointment.total_price == 3000
        assert appointment.special_requests == "None"
        assert appointment.recurrence_frequency  is None 
        assert appointment.recurrence_until is None 
        assert appointment.cancelled_by == None
        assert appointment.cancelled_at == None 
        assert appointment.bad_cancel == False 

    def test_appointment_str(self):
        appointment = AppointmentFactory()
        assert str(appointment) == f"Appointment by {appointment.customer.username} for {appointment.provider.username} on {appointment.date_start}"
    
    @pytest.mark.parametrize("status, is_valid", [
        ("pending", True),
        ("completed", True),
        ("accepted", True),
        ("rejected", True),
        ("rescheduled", True), 
        ("cancelled", True),
        ("ineligible", False),
        ("hakuntata", False),

          
    ])
    def test_appointment_statuses(self, status , is_valid):
        appointment = AppointmentFactory(status=status)
        if not is_valid :
            with pytest.raises(ValidationError):
                appointment.full_clean()
        else :
            assert status in ["pending", "completed" , "accepted", "rejected" ,"rescheduled", "cancelled"]

    def test_inactive_users_not_shown(self):
        appointment = AppointmentFactory(
    provider_profile=ProviderProfileFactory(user__is_active=False)
)

        active_appointments = Appointment.objects.all()
        assert appointment not in active_appointments 


        total_appointments = Appointment.all_objects.all()

        assert appointment in total_appointments 
    

    def test_valid_cancel_field_with_details(self):
        appointment = AppointmentFactory(
            status="cancelled",
            bad_cancel=True,
            cancelled_by=UserFactory(),
            cancelled_at= now(),
        )
        # Should not raise error
        appointment.full_clean()

    @pytest.mark.parametrize("use_user, use_time, bad_cancel", [
        (False, False, True),
        (True, False, False),
        (False, True, False),
        (True, True, True),
    ])
    def test_invalid_cancel_field_with_details(self , use_user, use_time, bad_cancel):
        user = UserFactory()
        cancelled_by = user if use_user else None
        cancelled_at = now() if use_time else None

        appointment = AppointmentFactory(
            status="completed",
            bad_cancel=bad_cancel,
            cancelled_by=cancelled_by,
            cancelled_at=cancelled_at,
        )

        with pytest.raises(ValidationError) as excinfo:
            appointment.full_clean()
        assert "Cancellation fields can only be set if the appointment is cancelled." in str(excinfo.value)

    
    def test_all_dates_aware(self):
        appointment= AppointmentFactory(status="cancelled" , cancelled_at = now())
        assert is_aware(appointment.date_start)
        assert is_aware(appointment.date_end)
        assert is_aware(appointment.date_added)
        assert is_aware(appointment.cancelled_at)






@pytest.mark.django_db
class TestNotificationPreferences:

    def test_preferences_creation(self):
        notifications = NotificationPreferencesFactory()
        assert notifications.pk is not None 
        assert notifications.user.pk is not None 
        assert notifications.preferences == "all"

    @pytest.mark.parametrize("preference, is_valid ", [
        ("all", True),
        ("reminders", True),
        ("none", True),
        ("maybe", False),
        ("notreally", False),
    ])
    def test_validity_choice_fields(self , preference , is_valid):
        notification = NotificationPreferencesFactory(preferences = preference)
        if not is_valid :
            with pytest.raises(ValidationError):
                notification.full_clean()
        else :
            assert notification.preferences in ["all", "reminders", "none"]




