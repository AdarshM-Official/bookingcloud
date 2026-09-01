# BookingCloud 📅

A **multi-tenant booking SaaS platform** built with Django. BookingCloud allows multiple independent businesses to register and manage appointments. Each business receives a fully branded, customer-facing booking website on its own unique subdomain.

---

## 🚀 Features

### For Businesses (Dashboard)
- **Business Profile** — Set up your brand identity: logo, banner, description, address, social links, custom brand colors.
- **Services Management** — Create and manage the services you offer, with pricing, duration, and descriptions.
- **Staff Management** — Add staff members, manage their schedules, availability, breaks, and leaves.
- **Bookings Management** — A premium table view of all appointments. Accept, decline, complete, or manage multi-service bookings.
- **Payroll** — Track staff salary (fixed/hourly/commission), incentives, deductions, and payment status.
- **Availability** — Set business opening/closing hours per day of the week. Mark time-off days.
- **Calendar View** — Visual calendar for all upcoming appointments.
- **Analytics** — Dashboard overview of key business metrics.

### For Customers (Tenant Website)
- **Public Business Website** — Each business gets a polished, standalone website on its own subdomain.
- **Services Browsing** — Browse all available services with prices and duration.
- **Multi-Service Booking** — Select multiple services from the cart UI and book them as a single combined appointment with accurate time slot calculation.
- **Single Service Booking** — Instant "Book Now" from any service card.
- **Real-Time Slot Availability** — Time slots are dynamically fetched based on the business's working hours, existing appointments, and combined service duration.
- **Staff Profile Page** — View the team of staff members at the business.

---

## 🏗️ Architecture

BookingCloud uses **logical multi-tenancy** — a single Django application with a shared database, where tenant (business) data is isolated by foreign key.

### Subdomain Routing

Requests are intercepted by a custom `TenantMiddleware` at the Django middleware layer:

| Traffic Type | URL Pattern (Dev) | URL Pattern (Prod) |
|---|---|---|
| Main SaaS Platform | `localhost:8000` | `bookingcloud.com` |
| Tenant / Business Site | `<slug>.localhost:8000` | `<slug>.bookingcloud.com` |

**Example tenant URLs:**
- `glowstudio.localhost:8000`
- `devapriya-beauty-parlour.localhost:8000`

When a subdomain is detected, `TenantMiddleware` attaches `request.tenant = <Business instance>` and switches the URL configuration to `bookingsaas/tenant_urls.py`, completely separating SaaS and tenant routes.

### Project Structure

```
bookingsaas/
├── apps/
│   ├── accounts/          # Custom user registration & authentication
│   ├── dashboard/         # Business dashboard (models, views, URLs)
│   │   ├── models.py      # All core models
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── utils/
│   └── website/           # Public-facing views
│       ├── views.py        # Main SaaS landing page views
│       ├── urls.py         # Main SaaS URL config
│       └── tenant_views.py # Per-tenant public website views
├── bookingsaas/
│   ├── settings.py
│   ├── urls.py             # Main SaaS URL routing
│   ├── tenant_urls.py      # Tenant subdomain URL routing
│   └── middleware.py       # TenantMiddleware
├── templates/
│   ├── base.html           # Main SaaS base (internal CSS)
│   ├── dashboard/          # Business dashboard templates (Tailwind CSS)
│   ├── landing/            # Public SaaS landing page templates
│   ├── registration/       # Login / signup templates
│   └── tenant/             # Per-tenant public website templates (Tailwind CSS)
├── static/
│   ├── css/
│   └── images/
├── media/                  # User-uploaded files (logos, staff images, gallery)
├── requirements.txt
└── manage.py
```

---

## 🗄️ Data Models

| Model | Description |
|---|---|
| `Business` | Core tenant entity. Contains business profile, branding, hours, social links, and a unique `slug`. |
| `BusinessTimeOff` | Blocks an entire date range as unavailable (e.g., public holidays). |
| `Service` | A bookable service offered by a business (name, price, duration). |
| `Staff` | A staff member with scheduling, availability, and payroll capabilities. |
| `StaffAvailability` | Per-day working hours for a staff member. |
| `StaffBreak` | Mid-day breaks for a staff member. |
| `StaffTimeOff` | Leave requests for a staff member (paid, unpaid, sick). |
| `StaffPayroll` | Monthly payroll records per staff member. |
| `Booking` | An appointment. Supports both a single service (FK) and multiple services (M2M via `services` field). |
| `BusinessImage` | Gallery images for a business. |

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.11+
- pip

### 1. Clone the Repository

```bash
git clone <repository-url>
cd bookingsaas
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Apply Migrations

```bash
python manage.py migrate
```

### 5. Create a Superuser

```bash
python manage.py createsuperuser
```

### 6. Run the Development Server

```bash
python manage.py runserver
```

---

## 🌐 Accessing the Application

### Main SaaS Platform
```
http://localhost:8000/
```

### Business Dashboard
After logging in:
```
http://localhost:8000/dashboard/
```

### Tenant / Business Public Site

Each registered business with a `slug` gets its own subdomain. Use `lvh.me` (a free DNS service that resolves all subdomains to `127.0.0.1`) for easy local testing.

**Setup:** In `bookingsaas/settings.py`, change:
```python
BASE_DOMAIN = 'lvh.me:8000'
```

**Example URLs:**
```
http://glowstudio.lvh.me:8000/
http://devapriya-beauty-parlour.lvh.me:8000/
http://fitzone.lvh.me:8000/
```

> **Note for Windows:** `*.localhost` wildcard subdomains are not reliably supported on Windows by default. Use `lvh.me` as a reliable alternative during development.

---

## 🎨 Frontend Stack

| Area | Technology |
|---|---|
| Main SaaS Landing | Internal CSS |
| Dashboard | Tailwind CSS (via CDN) |
| Tenant Public Sites | Tailwind CSS (via CDN) |
| Icons | Lucide Icons |
| Dynamic Content | Vanilla JavaScript |

Tenant websites dynamically apply the business's custom `primary_color` using CSS variables injected from the `Business` model, so each business site feels uniquely branded.

---

## 📦 Dependencies

```
Django==5.2.17
Pillow==12.3.0
asgiref==3.12.1
sqlparse==0.5.5
tzdata==2026.3
```

---

## 📌 Key Configuration (`settings.py`)

| Setting | Default | Description |
|---|---|---|
| `BASE_DOMAIN` | `localhost:8000` | Used to build subdomain URLs for each tenant. |
| `TENANT_PROTOCOL` | `http` | Set to `https` in production. |
| `ALLOWED_HOSTS` | `['.localhost', '127.0.0.1', '.lvh.me']` | Wildcard prefix allows all subdomain tenants. |
| `MEDIA_ROOT` | `BASE_DIR / 'media'` | Upload destination for logos, images, etc. |

---

## 🔒 Authentication

- Registration and login are handled by `apps/accounts`.
- Registering creates a new `Business` tenant linked to the user account.
- The business dashboard is fully protected — only the authenticated business owner can access it.
- The tenant public website (subdomain) is publicly accessible. Customers book as guests by providing their name, email, and phone number.

---

## 🛒 Multi-Service Booking Flow

1. Customer visits the tenant's Services page (e.g., `glowstudio.lvh.me:8000/services/`).
2. Customer checks multiple service cards — a floating cart bar slides up from the bottom showing the combined price and total duration.
3. Customer clicks **Continue to Book** → routed to `/book/multi/?services=1,3,5`.
4. Backend calculates the **total combined duration** and finds available time slots that fit the entire appointment block.
5. Customer fills in details, selects date + time, and submits.
6. A single `Booking` record is created with all services attached via the `services` ManyToManyField.
7. The booking appears in the business dashboard with all services listed with correct combined price and duration.

---

## 🚢 Production Deployment Notes

- Set `DEBUG = False` and configure `ALLOWED_HOSTS` with your production domain.
- Set `BASE_DOMAIN = 'bookingcloud.com'` and `TENANT_PROTOCOL = 'https'`.
- Configure a **wildcard DNS record**: `*.bookingcloud.com → your server IP`.
- Configure your web server (Nginx/Apache) to handle wildcard subdomains and proxy to Gunicorn/uWSGI.
- Use a production database (PostgreSQL recommended).
- Run `python manage.py collectstatic` and serve static files via your web server.
- Configure media file serving via Nginx or an object storage service (e.g., AWS S3).
