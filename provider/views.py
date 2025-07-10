from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from main.utils import get_calendar_service
from django.contrib import messages
# Create your views here.
from django.shortcuts import redirect 


@login_required(login_url="/login/")
def providerdashboard(request):
    if request.method == "POST":
        if request.POST.get("test"):
            service = get_calendar_service(request.user)
            event = {
                    'summary': 'Math Class',
                    'location': 'Online',
                    'description': 'learn p3 math.',
                    'start': {
                        'dateTime': '2025-07-10T17:25:00+05:00',
                        'timeZone': 'Asia/Karachi',
                    },
                    'end': {
                        'dateTime': '2025-07-10T18:00:00+05:00',
                        'timeZone': 'Asia/Karachi',
                    },
                    
                    
                    'attendees': [
                        {'email': 'sameeramin.com@gmail.com'},
                        {'email': 'uhanifu@gmail.com'},
                    ],
                    'reminders': {
                        'useDefault': False,
                        'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},
                        {'method': 'email', 'minutes': 10},
                        ],
                    },
                    }
            try:
                event = service.events().insert(calendarId='primary', body=event).execute()
            except Exception as e :
                messages.warning(request , "error occured")
                return redirect("providerdashboard")
            messages.success(request ,"Event created successfully")
            return redirect("providerdashboard")
           


    return render(request , "provider/providerdashboard.html")