from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

# Create your views here.


@login_required(login_url="/login/")
def providerdashboard(request):
    if request.method == "POST":
        if request.POST.get("customerdashboard"):
            return redirect("customerdashboard")
    return render(request , "provider/providerdashboard.html")