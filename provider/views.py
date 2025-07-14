from django.contrib import messages
from django.contrib.auth.decorators import login_required
# Create your views here.
from django.shortcuts import redirect, render

from main.utils import get_calendar_service


@login_required(login_url="/login/")
def providerdashboard(request):
    if request.method == "POST":
        if request.POST.get("myprofile"):
            return redirect("userprofile")
           
    return render(request , "provider/providerdashboard.html")