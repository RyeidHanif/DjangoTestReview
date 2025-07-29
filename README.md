

# DjangoAppointmentScheduler

**DjangoAppointmentScheduler** is a robust and fully-featured appointment scheduling system built using the Django web framework and Django REST Framework (DRF). It enables seamless booking, rescheduling, and management of appointments between customers and service providers, with tight integration into Google Calendar for real-time synchronization and availability tracking.

This application is designed to support both server-rendered views and a complete RESTful API interface. The system enforces strict policies for appointment handling, features automatic syncs and unavailability tracking via Google Calendar, and supports complex business logic such as pricing models and cancellation bans.

---

## Features

* Google Calendar integration with OAuth 2.0 authorization and refresh token management
* Google SSO and standard Django authentication
* Every registered user is a customer by default with the ability to become a provider
* Real-time availability checks based on provider’s Google Calendar and defined working hours
* Ability to reschedule or cancel appointments with email notifications
* Appointment recurrence support with price calculation based on fixed/hourly model
* Google Calendar and normal Email reminders
* Notification settings to either recieve all , some or no notifications 
* Robust provider dashboard:

  * Accept or reject new/rescheduled appointments
  * Block availability time slots
  * Track earnings, customer analytics, and revenue reports
* Full customer dashboard:

  * View and manage all appointments (pending, accepted, rescheduled, history)
  * Search and browse service providers
  * Initiate bookings with recurrence, pricing, and special requests
* Smart pricing system with fixed/hourly logic and automatic calculation for recurring bookings
* Ban system to automatically restrict users who violate the cancellation policy
* Custom analytics page for service providers showing revenue, bookings, and customer data
* Caching of static-heavy views for performance
* Optimized database queries using `select_related` and `prefetch_related`
* Paginated and searchable lists for both customers and providers
* Heavily customized Django Admin dashboard for internal admin operations
* DRF Spectacular-based API schema generation and live documentation at `/api/docs`

---

## User Flows

### Customers

* Sign up using Google SSO or standard registration
* Automatically assigned a customer profile
* Access a complete dashboard to manage appointments:

  * View upcoming, accepted, pending, or rescheduled appointments
  * Cancel or reschedule appointments
  * Browse active service providers and view their availability
  * Book new appointments and set recurrence options
  * View appointment history and full booking log
  * Manage profile settings, upload/change profile picture, or delete account
  * Upgrade to a service provider at any time by filling a provider profile form

### Providers

* Create a provider profile with service category, working hours, appointment duration, buffer time, and pricing model (fixed/hourly)
* Set Google Calendar-based availability automatically using submitted working hours
* Accept or reject pending or rescheduled appointment requests
* View all accepted appointments with full customer and time details
* Cancel appointments directly from the dashboard, with Google Calendar sync
* Submit custom availability blocks (e.g., vacation, personal leave) which:

  * Are created directly in Google Calendar
  * Invalidate any conflicting existing bookings
* Access analytics page to view:

  * Number of appointments
  * Total earnings and admin fee deduction
  * Top booking customers
* Modify provider profile or disconnect Google Calendar integration (not recommended, as it disables provider functionality)

---

## Cancellation Policy

To prevent abuse of the system and ensure fair scheduling:

> Any user — customer or provider — who cancels **three or more accepted appointments within 12 hours** of the appointment time, **within any rolling 30-day period**, will be automatically banned from the platform.

This enforcement is handled entirely server-side and tracked for each user account.

---

## Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/ryeidhanif/DjangoAppointmentScheduler.git
cd DjangoAppointmentScheduler
```

### 2. Set Up a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create a PostgreSQL Database

Set up a PostgreSQL database manually or using tools like pgAdmin. Then configure your `.env` file with:

```ini
SECRET_KEY = your_app_secret_key
POSTGRES_USER = your_db_user
POSTGRES_PASSWORD = db_password
EMAIL_HOST_PASSWORD = email_host_password
BASE_URL=http://127.0.0.1:8000/
```

### 5. Add Google API Credentials

Create OAuth 2.0 credentials from the Google Developer Console and add them to your `.env`:

```ini
client_id = your google client id 
client_secret = your google client secret
```

### 6. Apply Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Run the Development Server

```bash
python manage.py runserver
```


## API Authentication & Token Handling

This project supports JWT-based token authentication with access and refresh tokens.

* `POST /api/signup`
  Create a new user account with `username` and `password`.

* `POST /api/token`
  Obtain access and refresh tokens.
  Payload:

  ```json
  {
    "username": "your_username",
    "password": "your_password"
  }
  ```

* `POST /api/token/refresh`
  Refresh your access token using the refresh token.
  Payload:

  ```json
  {
    "refresh": "your_refresh_token"
  }
  ```

* `GET /api/welcome`
  Returns a welcome message. Requires a valid access token.

---

The full list of available endpoints is documented using `drf-spectacular` at:

```
/api/docs
```


* `/api/providers/available/slots` – \[placeholder]
* `/api/appointments/create/` – \[placeholder]
* `/api/appointments/reschedule/` – \[placeholder]
* `/api/appointments/history/` – \[placeholder]
* `/api/analytics/provider/` – \[placeholder]
* `/api/customer/delete/` – \[placeholder]
* `/api/provider/block-availability/` – \[placeholder]
* `/api/calendar/reconnect/` – \[placeholder]
* `/api/notifications/settings/` – \[placeholder]

---

## Development Notes

* Google Calendar OAuth refresh tokens expire every 14 days. Providers must periodically re-authenticate to maintain integration.
* Google disconnection disables all provider functions. Calendar sync is mandatory for scheduling.
* All critical queries are optimized using `select_related` or `prefetch_related` for performance.
* Static-heavy views are cached with appropriate headers to minimize server load.
* The Django Admin dashboard has been customized extensively for backend management and monitoring but is not exposed as a public feature.

---


## License
MIT Licence 2025


