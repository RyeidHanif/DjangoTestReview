import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Permission, User
from django.shortcuts import redirect, render
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow

from .forms import ProviderForm
from .models import CustomerProfile, ProviderProfile, User, Appointment , NotificationPreferences 
from django.contrib.admin.views.decorators import staff_member_required
from django.views import View

from django.views.generic import ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from django.utils.decorators import method_decorator
from collections import Counter
from main.calendar_client import GoogleCalendarClient


# Create your views here.


class Home(TemplateView):
    template_name = "main/home.html"

home = Home.as_view()



# simple , CBV would add complexity 
@login_required(login_url="/login/")
def redirectiondashboard(request):
    """temporary dashboard to redirect  different users to their respective places"""
    user = request.user
    prefs, created = NotificationPreferences.objects.get_or_create(user=request.user)
    if hasattr(user, "customerprofile") and hasattr(user, "providerprofile"):
        return render(request, "main/redirectdashboard.html")
    elif hasattr(user, "customerprofile"):
        return redirect("customerdashboard")
    elif hasattr(user, "providerprofile"):
        return redirect("connect_to_calendar")
    messages.error(request, "you do not have a profile , please create one ")

    return redirect("profile_creation")


def profile_creation(request, n):
    """
    profile creation system which uses the provider form and parameter n to divide choices

    user id and phone number are use from the session and then deleted
    n is used to differentiate between users who want to be both and those
    who want to be a provider
    if n is given as "both" , then a customer profile for that user is also created
    the user is then redirected to the login page
    """
    user_id = request.session.get("temp_user_id")
    phone = request.session.get("temp_phone")
    if not user_id:
        return redirect("signup")
    if request.method == "POST":
        provider_form = ProviderForm(request.POST , request.FILES)
        if provider_form.is_valid():

            user = User.objects.get(id=user_id)

            if ProviderProfile.objects.filter(user=user).exists():
                return redirect("login")

            profile = provider_form.save(commit=False)
            profile.user = user
            profile.phone_number = phone
            profile.save()

            del request.session["temp_user_id"]
            del request.session["temp_phone"]
            if n == "both":
                CustomerProfile.objects.create(user=user, phone_number=phone)
            return redirect("login")

    provider_form = ProviderForm()
    return render(request, "main/profile_creation.html", {"form": provider_form})



@login_required(login_url="/login/")
def connect_to_calendar(request):
    """Displays the page to allow the user to connect to their google calendar"""
    user = request.user
    profile = ProviderProfile.objects.get(user=user)
    if profile.google_calendar_connected:
        messages.info(request, "you are connected to calendar")
        return redirect("providerdashboard")
    else:
        if request.method == "POST":
            return redirect("connect_google")

        return render(request, "main/connect_to_calendar.html")


def connect_google(request):
    """Creates the authorization url which the user is redirected to to allow for the connection"""
    calendar_client = GoogleCalendarClient()

    auth_url = calendar_client.create_auth_url()
    return redirect(auth_url)

def oauth2callback(request):
    """authenticates the user ,stores credentials and redirects to dashboard

    google authentication client credentials are loaded from the credentials.json file
    stored in the BASE directory .
    Scopes allotted are full permissions and the redirect uri matches that in
    the google oauth credential settings to allow google to redirect the user back here
    the authorization code sent by google is exchanged for access and refresh tokens
    which are then stored in the ProvideProfile model columns to be used later
    """
    calendar_client = GoogleCalendarClient()
    calendar_client.google_calendar_callback(request)
    return redirect("providerdashboard")

class CancellationPolicy(TemplateView):
    template_name = "main/cancellationpolicy.html"

cancellation_policy = CancellationPolicy.as_view()


@method_decorator(staff_member_required, name='dispatch')
class AdminDashboard(View , LoginRequiredMixin):
    def get(self , request , *args , **kwargs):
        admin_revenue= 0
        revenue = 0
        users = User.objects.all()
        appointments = Appointment.objects.select_related('provider__providerprofile').all()
        providers = ProviderProfile.objects.all()
        customers = CustomerProfile.objects.all()
        for appointment in appointments :
            if appointment.status in ["completed", "accepted"]:
                revenue += appointment.total_price
                admin_revenue = 0.05 * revenue
        categories = Counter()
        statuses = Counter()
        provider_dict = Counter()

        for appointment in appointments:
            categories[appointment.provider.providerprofile.service_category] += 1
            statuses[appointment.status] += 1
            provider_dict[appointment.provider.username] += 1

        total_appointments = sum(categories.values())

        categories = dict(categories.most_common())
        provider_dict = dict(provider_dict.most_common())
        statuses =dict(statuses)

        return render(request , "main/admin_dashboard.html", {"revenue": revenue , "myrevenue": admin_revenue , "statuses": statuses , "all_appointments": appointments , "all_providers": providers, "all_customers": customers, "total_appointments" : total_appointments, "users":users , "provider_dict": provider_dict , "categories": categories})
    
    def post(self , request , *args , **kwargs):
        if request.POST.get("toggle_active"):
            user_id = request.POST.get("toggle_active")
            current_user = User.objects.get(id=user_id)
            if current_user.is_active:
                current_user.is_active = False
            else:
                current_user.is_active = True
            current_user.save()
        if request.POST.get("delete"):
            user_id = request.POST.get("delete")
            user = User.objects.get(id=user_id)
            if user :
                user.delete()
            else :
                messages.error(request,"user does not exist")
        return self.get(request)

        
admin_dashboard = AdminDashboard.as_view()






@method_decorator(staff_member_required, name='dispatch')
class ViewCustomerProfile(TemplateView):
    template_name = "main/view_customer_profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = User.objects.get(id=kwargs['userID'])
        context["user"] = user
        context["user_customer_profile"] = CustomerProfile.objects.get(user=user)
        context["appointments_customer"] = Appointment.objects.filter(customer=user)
        return context

view_customer_profile = ViewCustomerProfile.as_view()

@method_decorator(staff_member_required, name='dispatch')
class ViewProviderProfile(TemplateView):
    template_name = "main/view_provider_profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = User.objects.get(id=kwargs['userID'])
        context["user"] = user
        context["user_provider_profile"] = ProviderProfile.objects.get(user=user)
        context["appointments_provider"] = Appointment.objects.filter(provider=user)
        return context

view_provider_profile = ViewProviderProfile.as_view()