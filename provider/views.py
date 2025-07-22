from django.contrib import messages
from django.contrib.auth.decorators import login_required
# Create your views here.
from django.shortcuts import redirect, render

from main.utils import get_calendar_service


@login_required(login_url="/login/")
def provider_dashboard(request):
    if request.method == "POST":
        if request.POST.get("test"):
            service = get_calendar_service(request.user)
            # this is a test event , to see if calendar integration is woking properly
            event = {
                "summary": "Chemiistry Class",
                "location": "Online",
                "description": "learn p3 chem.",
                "start": {
                    "dateTime": "2025-07-11T10:04:00+05:00",
                    "timeZone": "Asia/Karachi",
                },
                "end": {
                    "dateTime": "2025-07-11T10:30:00+05:00",
                    "timeZone": "Asia/Karachi",
                },
                "attendees": [
                    {"email": "uhanifu@gmail.com"},
                ],
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "email", "minutes": 24 * 60},
                        {"method": "email", "minutes": 10},
                        {"method": "popup", "minutes": 10},
                    ],
                },
            }
            try:
                event = (
                    service.events()
                    .insert(calendarId="primary", body=event, sendUpdates="all")
                    .execute()
                )
            except Exception as e:
                messages.warning(request, "error occured")
                return redirect("provider_dashboard")
            messages.success(request, "Event created successfully")
            return redirect("provider_dashboard")

        if request.POST.get("customer_dashboard"):
            return redirect("customer_dashboard")
    return render(request, "provider/provider_dashboard.html")
