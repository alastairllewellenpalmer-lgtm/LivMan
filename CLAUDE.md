# CLAUDE.md — LivMan (Horse Livery Management System)

## Project Overview

LivMan is a Django web application for managing horse livery operations. It tracks horses by location, manages owners, generates invoices, monitors horse health, and handles billing for extra services. The frontend uses Django templates with Tailwind CSS (CDN) and HTMX for interactive UI.

## Tech Stack

- **Backend**: Python 3.11+, Django 5.x
- **Database**: SQLite (dev), PostgreSQL (prod via `DATABASE_URL`)
- **Frontend**: Django templates, Tailwind CSS (CDN), HTMX 1.9.10, Crispy Forms (tailwind pack)
- **Task Queue**: Celery 5.3+ with Redis broker
- **PDF Generation**: ReportLab (with WeasyPrint fallback logic in code)
- **Static Files**: WhiteNoise with compressed manifest storage
- **Deployment**: Vercel (Python 3.11 serverless runtime)

## Repository Layout

```
LivMan/                          # Repo root AND Django project package (horse_management)
├── manage.py                    # Django CLI entrypoint
├── __init__.py                  # Imports Celery app
├── settings.py                  # Django settings (also at horse_management/settings.py)
├── urls.py                      # Root URL config
├── celery.py                    # Celery app configuration
├── wsgi.py / asgi.py            # WSGI/ASGI entry points
├── requirements.txt             # Python dependencies (pip)
├── .env.example                 # Environment variable template
├── vercel.json                  # Vercel deployment config
├── build_files.sh               # Vercel build script
│
├── core/                        # Main app: Horse, Owner, Location, Placement, Invoice models
│   ├── models.py                # Core domain models
│   ├── views.py                 # Dashboard + CRUD views
│   ├── forms.py                 # Core model forms
│   ├── urls.py                  # Routes: /, /horses/, /owners/, /locations/, /placements/
│   ├── admin.py                 # Django admin registration
│   └── management/commands/     # import_data, load_csv_data commands
│
├── invoicing/                   # Invoice generation, PDF/CSV export
│   ├── models.py                # (uses core.Invoice, core.InvoiceLineItem)
│   ├── views.py                 # Invoice CRUD, PDF/CSV export, send/mark-paid
│   ├── services.py              # InvoiceService: calculation logic
│   ├── pdf.py                   # PDF generation (WeasyPrint/ReportLab)
│   ├── utils.py                 # Date formatting helpers
│   ├── forms.py                 # Invoice forms
│   └── urls.py                  # Routes: /invoicing/
│
├── health/                      # Health tracking: vaccinations, farrier, worming, vet, breeding
│   ├── models.py                # Vaccination, FarrierVisit, WormingTreatment, VetVisit, etc.
│   ├── views.py                 # CRUD views for all health record types
│   ├── forms.py                 # Health record forms
│   └── urls.py                  # Routes: /health/
│
├── billing/                     # Extra charges and service providers
│   ├── models.py                # ExtraCharge, ServiceProvider
│   ├── views.py                 # CRUD views
│   ├── forms.py                 # Billing forms
│   └── urls.py                  # Routes: /billing/
│
├── notifications/               # Celery tasks for email reminders
│   ├── tasks.py                 # Scheduled tasks (vaccination, farrier, invoice reminders)
│   └── emails.py                # Email composition functions
│
├── templates/                   # All HTML templates (~52 files)
│   ├── base.html                # Base layout (Tailwind + HTMX)
│   ├── dashboard.html           # Main dashboard
│   ├── horses/                  # Horse CRUD templates
│   ├── owners/                  # Owner CRUD templates
│   ├── locations/               # Location CRUD templates
│   ├── placements/              # Placement templates
│   ├── invoicing/               # Invoice templates
│   ├── health/                  # Health record templates
│   ├── billing/                 # Billing templates
│   └── registration/            # Auth templates (login, etc.)
│
├── static/css/                  # Custom CSS
├── data/                        # CSV import utilities
└── horse_management/            # Django project config (symlinked/duplicated settings)
```

## Quick Start (Development)

```bash
# 1. Create and activate virtualenv
python -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment
cp .env.example .env
# Edit .env as needed (defaults work for local dev)

# 4. Run migrations
python manage.py migrate

# 5. Create admin user
python manage.py createsuperuser

# 6. Start dev server
python manage.py runserver
```

The app will be available at `http://127.0.0.1:8000/`. Login is required for all views.

## Key Commands

| Command | Purpose |
|---------|---------|
| `python manage.py runserver` | Start development server |
| `python manage.py migrate` | Apply database migrations |
| `python manage.py makemigrations` | Generate migrations after model changes |
| `python manage.py createsuperuser` | Create admin user |
| `python manage.py import_data` | Import data from CSV files |
| `python manage.py collectstatic` | Collect static files for production |
| `celery -A horse_management worker -l info` | Start Celery worker |
| `celery -A horse_management beat -l info` | Start Celery beat scheduler |

## Environment Variables

Configured via `.env` file (see `.env.example`). Key variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DEBUG` | `True` | Debug mode |
| `SECRET_KEY` | insecure default | Django secret key |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Allowed HTTP hosts |
| `DATABASE_URL` | None (uses SQLite) | PostgreSQL connection string |
| `EMAIL_BACKEND` | console backend | Email delivery backend |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery message broker |

## Testing

pytest and pytest-django are in requirements.txt but **no test files currently exist**. When adding tests:

- Use pytest-django as the test runner
- Place test files in each app directory (e.g., `core/tests.py` or `core/tests/`)
- Set `DJANGO_SETTINGS_MODULE=horse_management.settings` in `conftest.py` or `pytest.ini`
- Run with: `pytest`

## URL Structure

| Prefix | App | Purpose |
|--------|-----|---------|
| `/` | core | Dashboard |
| `/horses/` | core | Horse CRUD |
| `/owners/` | core | Owner CRUD |
| `/locations/` | core | Location CRUD |
| `/placements/` | core | Placement CRUD |
| `/invoicing/` | invoicing | Invoice generation, PDF/CSV export |
| `/health/` | health | Vaccinations, farrier, worming, vet, breeding |
| `/billing/` | billing | Extra charges, service providers |
| `/admin/` | django.contrib.admin | Django admin panel |
| `/accounts/` | django.contrib.auth | Authentication (login/logout) |

## Code Conventions

### Models
- CamelCase singular names: `Horse`, `Owner`, `Invoice`
- Use `TextChoices` for choice fields
- Properties for computed values (e.g., `current_placement`, `active_horses`)
- `Decimal` type for all monetary values (never float)
- `is_active` boolean for soft deletes
- `created_at` / `updated_at` auto-timestamp fields
- Validation in `clean()` methods (e.g., placement overlap checking)

### Views
- Class-based views: `{Model}ListView`, `{Model}DetailView`, `{Model}CreateView`, `{Model}UpdateView`
- Function-based views for custom logic (e.g., `dashboard()`, `horse_move()`)
- `LoginRequiredMixin` on all protected views
- `select_related()` and `prefetch_related()` in `get_queryset()` to prevent N+1 queries

### URLs
- RESTful patterns: `/resource/`, `/resource/<id>/`, `/resource/<id>/edit/`, `/resource/<id>/delete/`
- Action endpoints: `/resource/<id>/action/` (e.g., `/invoices/<id>/send/`)

### Templates
- Extend `base.html` for all pages
- Tailwind CSS classes for styling (loaded via CDN, no build step)
- HTMX attributes for AJAX interactions
- Crispy forms with tailwind template pack for form rendering

### Django Settings
- Settings module: `horse_management.settings`
- Timezone: `Europe/London`, Language: `en-gb`
- WhiteNoise middleware for static file serving
- Debug toolbar auto-enabled when `DEBUG=True`

## Architecture Notes

### Invoice Generation
The invoicing system uses `InvoiceService` in `invoicing/services.py` for all calculation logic. Invoices are generated per-owner per-month, with line items calculated from placement dates and rate types. The service handles placement overlap within billing periods.

### Celery Tasks
Automated notification tasks in `notifications/tasks.py`:
- `send_vaccination_reminders()` — daily vaccination due alerts
- `send_farrier_reminders()` — farrier visits due within 2 weeks
- `send_overdue_invoice_reminders()` — overdue payment alerts
- `send_ehv_reminders()` — EHV vaccination for pregnant mares
- `check_invoice_status()` — auto-mark sent invoices as overdue

These require Redis and a running Celery worker + beat process.

### Deployment (Vercel)
- Deployed as Python serverless on Vercel (see `vercel.json`)
- Vercel URLs are auto-added to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`
- SSL handled at Vercel edge; `SECURE_SSL_REDIRECT` is disabled
- Static files served via WhiteNoise

## Linting / Formatting

No linting or formatting tools are currently configured. There is no `pyproject.toml`, `.flake8`, or pre-commit config.

## CI/CD

No CI/CD pipeline is configured. Deployment is via Vercel's Git integration.
