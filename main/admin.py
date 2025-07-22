from django.contrib import admin

from .models import AnalyticsApi, Appointment, CustomerProfile, ProviderProfile

admin.site.register(ProviderProfile)
admin.site.register(CustomerProfile)
admin.site.register(Appointment)
admin.site.register(AnalyticsApi)


# Register your models here.
