from django.contrib import admin

from .models import AnalyticsApi, Appointment, CustomerProfile, ProviderProfile ,NotificationPreferences

admin.site.register(ProviderProfile)
admin.site.register(CustomerProfile)
admin.site.register(Appointment)
admin.site.register(AnalyticsApi)
admin.site.register(NotificationPreferences)


# Register your models here.
