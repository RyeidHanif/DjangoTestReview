from django.contrib import admin

from .models import AnalyticsApi, Appointment, CustomerProfile, ProviderProfile ,NotificationPreferences , Cancellation

admin.site.register(ProviderProfile)
admin.site.register(CustomerProfile)
admin.site.register(Appointment)
admin.site.register(AnalyticsApi)
admin.site.register(NotificationPreferences)
admin.site.register(Cancellation)


# Register your models here.
