from django.contrib.auth.models import User
from rest_framework import serializers

from main.models import Appointment, ProviderProfile


class RegisterSerializer(serializers.ModelSerializer):
    '''
    Model Serializer based on the default Django User Class to create a new user '''
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def create(self, validated_data):
        user = User(
            username=validated_data["username"], email=validated_data.get("email", "")
        )
        user.set_password(validated_data["password"])  # Hashes the password
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    '''
    Basic Model Serializer meant to be used as a nested serializer in other serializers
    to show user data 
    '''
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class ProviderProfileSerializer(serializers.ModelSerializer):
    '''
    Model Serializer based on the provider profile containing all the fields for the user to see 
    '''

    user = UserSerializer(read_only=True)

    class Meta:
        model = ProviderProfile
        fields = [
            "user",
            "phone_number",
            "service_category",
            "service_name",
            "pricing_model",
            "duration_mins",
            "start_time",
            "end_time",
            "rate",
            "buffer",
        ]


class AppointmentSerializer(serializers.ModelSerializer):
    '''
    Model Serializer based on the appointment model 
    It has Provider and Customer as nested user serializers to show data about each user 
    '''
    provider = UserSerializer(read_only=True)
    customer = UserSerializer(read_only=True)

    class Meta:

        model = Appointment
        fields = [
            "provider",
            "customer",
            "date_start",
            "date_end",
            "date_added",
            "status",
            "total_price",
            "special_requests",
            "recurrence_frequency",
            "recurrence_until",
        ]


class ProviderAnalyticsSerializer(serializers.Serializer):
    '''
    Normal Serializer which gets data in the ApiView and displays analytics data to the user
    '''
    provider = serializers.CharField(source="provider.username")
    appointments = AppointmentSerializer(many=True, read_only=True)
    total_appointments = serializers.IntegerField()
    admin_revenue = serializers.FloatField()
    my_revenue = serializers.FloatField()
    statuses = serializers.DictField(child=serializers.IntegerField())


class ViewAllProvidersSerializer(serializers.ModelSerializer):
    '''
    Model Serialier based on provider profile with many set to True in the API view to allow 
    all the providers and their profiles to be seen 
    '''
    user = UserSerializer(read_only=True)

    class Meta:
        model = ProviderProfile
        fields = [
            "user",
            "service_category",
            "start_time",
            "end_time",
            "rate",
            "pricing_model",
        ]



class WelcomeSerializer(serializers.Serializer):
    '''
    Serializer required forthis simple function for it to be displayed properly in the API documentation by drf-spectacular
    '''
    message = serializers.CharField()



class SlotSerializer(serializers.Serializer):
    '''
    allows for the slots to be displayed in an organized matter ,separated dates and times '''
    start_date = serializers.DateField()
    start_time = serializers.TimeField()
    end_date = serializers.DateField()
    end_time = serializers.TimeField()
    timezone = serializers.CharField()
