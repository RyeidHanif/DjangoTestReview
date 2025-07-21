from django.contrib import admin

from .models import Appointment, CustomerProfile, ProviderProfile, AnalyticsApi

admin.site.register(ProviderProfile)
admin.site.register(CustomerProfile)
admin.site.register(Appointment)
admin.site.register(AnalyticsApi)


# Register your models here.
