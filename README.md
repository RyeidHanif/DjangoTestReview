# Django Appointment Scheduling System

This is a full-featured appointment scheduling platform built with Django. It enables service providers to manage bookings, sync with Google Calendar, and handle client relationships, while customers can effortlessly schedule, view, or manage their appointments.

 Features

 Core Functionality

- Google Calendar integration for real-time sync
- JWT-based authentication system with optional Google SSO
- Separate dashboards for providers and customers
- Complete CRUD operations on appointments, availability, and profiles
- Notification system with email and in-app reminders
- Recurring appointments with dependency handling
- Buffer time logic to prevent back-to-back booking issues
- Analytics dashboard for service providers

---

 Features for Providers

- Connect Google Calendar and auto-sync events
- View all pending, confirmed, and past appointments
- Accept or reject appointment requests
- Cancel or reschedule bookings
- Set working hours and buffer times via profile settings
- Block unavailable slots (reflected on calendar)
- Configure recurring appointments
- Auto-calculate total price based on hourly/fixed pricing models
- View analytics: revenue, customer history, total appointments
- Upload profile pictures and service descriptions

---

 Features for Customers

- Search and view providers grouped by service category
- Instantly view daily or weekly availability
- Create, reschedule, or cancel appointments easily
- Double booking prevention
- Automatic Google Calendar event generation
- Set notification preferences
- Dashboard access to profile, history, and settings

---

 API Documentation

API is built using Django REST Framework.

- Docs available at: [`/api/docs/`](http://yourdomain.com/api/docs/)  
- Authentication: **JWT (JSON Web Tokens)**  
  - Sign up: `POST /api/signup/`
  - Login: `POST /api/token/` → returns `access` + `refresh` tokens
  - Refresh token: `POST /api/token/refresh/`
  - Include access token in requests:
    ```http
    Authorization: Bearer <access_token>
    ```

> {to do: Add actual deployment URL for the API documentation link}

---

 Tech Stack

- Backend:** Django, Django REST Framework  
- Authentication:** JWT via `djangorestframework-simplejwt`, Google SSO via `django-allauth`, django's default authentication system
- Calendar Integration: Google Calendar API
- Database: Postgre Sql
- Email Backend: django Email backend
- Frontend: Html CSS(bootstrap) + Django's Default Templating engine 
- Documentation:** `drf-spectacular` 

---

API Authentication Flow

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/signup/` | `POST` | Create user account |
| `/api/token/` | `POST` | Login, get `access` + `refresh` |
| `/api/token/refresh/` | `POST` | Get new `access` token using `refresh` |
| (Protected endpoints) | `GET/POST/...` | Use header: `Authorization: Bearer <access_token>` |

---

 Installation & Setup

```bash
# Clone the repository
git clone https://github.com/ryeidhanif/DjangoAppointmentTestReview.git
cd DjangoAppointmentSchedulingSystem

# Create a virtual environment
python -m venv venv
source venv/bin/activate 

# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Start the development server
python manage.py runserver


