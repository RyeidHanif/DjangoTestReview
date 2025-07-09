from django.contrib import admin

from .models import Appointment, CustomerProfile, ProviderProfile

admin.site.register(ProviderProfile)
admin.site.register(CustomerProfile)
admin.site.register(Appointment)


# Register your models here.
