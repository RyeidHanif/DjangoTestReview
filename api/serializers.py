from django.contrib.auth.models import User
from rest_framework import serializers

from main.models import Appointment, ProviderProfile


class RegisterSerializer(serializers.ModelSerializer):
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
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class ProviderProfileSerializer(serializers.ModelSerializer):

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
    provider = serializers.CharField(source="provider.username")
    appointments = AppointmentSerializer(many=True, read_only=True)
    total_appointments = serializers.IntegerField()
    admin_revenue = serializers.FloatField()
    my_revenue = serializers.FloatField()
    statuses = serializers.DictField(child=serializers.IntegerField())


class ViewAllProvidersSerializer(serializers.ModelSerializer):
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
    message = serializers.CharField()



class SlotSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    start_time = serializers.TimeField()
    end_date = serializers.DateField()
    end_time = serializers.TimeField()
    timezone = serializers.CharField()
