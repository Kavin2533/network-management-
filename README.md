# NetManage — Network Device Management System

A full-stack Flask web application for tracking, organizing, and monitoring
the live reachability of network devices (routers, switches, firewalls,
servers, and access points). Built as a portfolio project demonstrating
production-oriented Flask architecture: the application factory pattern,
blueprints, SQLAlchemy ORM models, Flask-WTF form validation, Flask-Login
authentication, and a live ICMP ping status engine.

## Features

- **Authentication** — secure login/logout with hashed passwords (Werkzeug), full route protection via `@login_required`, and a self-service change-password flow.
- **Device inventory** — add, edit, delete, and search devices by name, IP address, or location.
- **Validation** — IPv4 format enforcement (`ipaddress` module) and duplicate-IP rejection with inline form errors.
- **Live status engine** — ping any device on demand, or refresh every device at once, via AJAX (Fetch API) — no full page reloads.
- **Dashboard** — at-a-glance metric cards (total / online / offline / unknown) and a recently-checked devices table.
- **Clean architecture** — application factory pattern, blueprints, and strict separation of models / forms / routes / templates.
- **Polished UI** — responsive Bootstrap 5 layout with a collapsible sidebar, Font Awesome icons, and custom status-badge styling.
- **Custom error pages** — styled 404 and 500 pages.

## Tech Stack

| Layer          | Technology                                   |
|----------------|-----------------------------------------------|
| Backend        | Python 3.10+, Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF |
| Database       | SQLite (via SQLAlchemy ORM)                  |
| Frontend       | Bootstrap 5, Font Awesome, Vanilla JS (Fetch API) |
| Status engine  | Python `subprocess` (native OS `ping`)       |

## Project Structure

```
network-management/
├── app.py                  # Application factory, extension init, error handlers
├── config.py               # Environment-based configuration
├── models.py                # SQLAlchemy models: User, Device
├── forms.py                 # Flask-WTF forms + custom validators
├── routes.py                # auth_bp (login/logout/password) + main_bp (dashboard/CRUD/ping)
├── init_db.py                # Creates tables + seeds a default admin user
├── requirements.txt
├── README.md
├── static/
│   ├── css/style.css
│   └── js/status_ping.js
└── templates/
    ├── base.html
    ├── _flash_messages.html
    ├── login.html
    ├── dashboard.html
    ├── device_list.html
    ├── device_form.html
    ├── change_password.html
    ├── 404.html
    └── 500.html
```

## Setup

```bash
# 1. Clone / unzip the project, then move into it
cd network-management

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Initialize the database (creates tables + a default admin user)
python init_db.py

# 5. Run the app
python app.py
```

Visit **http://127.0.0.1:5000** in your browser.

**Default login:** `admin` / `admin123` — change this immediately via the
"Change Password" menu after your first login.

## Configuration

`config.py` supports three environments, selected via the `FLASK_ENV`
environment variable (defaults to `development`):

```bash
export FLASK_ENV=production
export SECRET_KEY="a-long-random-value"   # required in production
python app.py
```

| Config              | Notes                                              |
|---------------------|-----------------------------------------------------|
| `development`       | Debug mode on, uses `database.db` in project root   |
| `production`        | Debug off, **requires** `SECRET_KEY` env var         |
| `testing`           | In-memory SQLite, CSRF disabled for test convenience |

## How the Ping Engine Works

`routes.py` shells out to the operating system's native `ping` binary via
`subprocess.run()` with a fixed argument list (never `shell=True`, never
string-interpolated), so there is no command-injection surface even though
the target has already passed strict IPv4 validation at the form layer.
Windows uses `ping -n 1 -w <ms>`; Linux uses `ping -c 1 -W <s>`; macOS uses
`ping -c 1 -t <s>` — this OS branching lives in `ping_host()` in `routes.py`.

Each ping updates the device's `status` and `last_checked` columns and
returns JSON, which `status_ping.js` uses to patch the specific table row
in place (no full-page reload). The dashboard's "Refresh All Statuses"
button hits a separate bulk endpoint that pings every device in one request.

## Security Notes

- Passwords are never stored in plaintext — only Werkzeug-generated hashes.
- CSRF protection is enabled globally (`Flask-WTF`'s `CSRFProtect`), covering
  both form submissions and the JSON `fetch()` calls used by the ping engine.
- All device-management routes require an authenticated session.
- Device deletion is POST-only (never triggered by a bare GET link) and
  gated behind a confirmation modal.
- `SECRET_KEY` must be supplied via environment variable in production;
  the app refuses to start otherwise.

## Possible Extensions

- Role-based access control (admin vs. read-only viewer)
- Background scheduler (APScheduler / Celery) for automatic periodic pings instead of on-demand only
- REST API layer for third-party integrations
- Device grouping / tagging and bulk import via CSV
- Historical uptime charts per device
