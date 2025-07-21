from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

# Create your views here.

@login_required(login_url="/login/")
def customerdashboard(request):
    if hasattr(request.user ,'providerprofile'):
        display = "Go to provider Dashboard"
        if request.method == "POST":
            if request.POST.get("providerside"):
                return redirect("providerdashboard")
        
    else :
        display = "Become a Service Provider "
        if request.method == "POST":
            if request.POST.get("providerside"):
                return redirect("profile_creation")
    
    
        

    return render(request , "customer/customerdashboard.html", {"user": request.user , "display": display})

