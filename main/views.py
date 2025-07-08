from django.shortcuts import render
from django.contrib.auth.decorators import login_required


# Create your views here.


def home(request):
    return render(request, "main/home.html")


@login_required(login_url="/login/")
def dashboard(request):
    return render(request, "main/dashboard.html")
