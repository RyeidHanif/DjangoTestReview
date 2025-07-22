from django.contrib.auth.models import User
from django.shortcuts import render
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# Create your views here.
from main.models import AnalyticsApi

from .serializers import RegisterSerializer


class SignUpUser(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer


signupuser = SignUpUser.as_view()


class WelcomeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": f"Welcome, {request.user.username}!"})


welcome = WelcomeView.as_view()
