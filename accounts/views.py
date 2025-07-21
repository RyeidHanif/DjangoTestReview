from django.shortcuts import redirect, render

from .forms import SignUpForm

# Create your views here.


def signup(request):

    if request.method == "POST":
        suform = SignUpForm(request.POST)
        if suform.is_valid():
            suform.save()
            return redirect("login")

    suform = SignUpForm()
    return render(request, "accounts/signup.html", {"form": suform})
