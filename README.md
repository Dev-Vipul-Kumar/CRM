# Contract Management System (CRM)

A professional, full-featured web-based Contract Management System built with Django for the Indian Aviation Academy.

## Features

- **Authentication** — Login, logout, "Remember Me", role-based access
- **User Management** — Admin creates/manages Admin, Manager, Employee users
- **Contracts** — Full CRUD with auto-generated contract numbers (CTR-YYYY-XXXX)
- **Version Control** — Every document upload creates a new version; full history preserved
- **Assignment** — Assign contracts to multiple users
- **Approval Workflow** — Submit → Review → Approve / Reject / Request Changes
- **Digital Signatures** — Canvas-based signature pad, per-user signature requests
- **Renewal Alerts** — Automated expiry thresholds (7 / 15 / 30 days)
- **Notifications** — In-app alert center with unread badge
- **Audit Trail** — Every significant action logged with user + timestamp + IP
- **Reports** — Status summary, expiry calendar, CSV export
- **Dashboard** — Role-specific dashboards with live database statistics
- **Responsive UI** — Bootstrap 5, professional sidebar layout

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Seed demo data
python manage.py seed_data

# Start development server
python manage.py runserver
```

Open http://127.0.0.1:8000/

## Demo Credentials

| Role     | Username  | Password    |
|----------|-----------|-------------|
| Admin    | admin     | admin123    |
| Manager  | manager1  | manager123  |
| Employee | employee1 | employee123 |

## Management Commands

```bash
# Check and generate renewal reminders (run daily via scheduler)
python manage.py check_renewals

# Re-seed demo data
python manage.py seed_data
```

## Project Structure

```
CRM/
├── config/          — Project settings and URL routing
├── accounts/        — Users, roles, departments, authentication
├── contracts/       — Contracts, versions, assignments, categories
├── approvals/       — Approval workflow
├── signatures/      — Digital signature workflow
├── notifications/   — In-app notification system
├── audit/           — Audit trail and activity logs
├── dashboard/       — Role-based dashboards
├── reports/         — Reports and CSV export
├── templates/       — HTML templates
├── static/          — CSS, JS, images
└── media/           — Uploaded contract documents
```

## Technology Stack

- **Backend**: Django 6.1, Python 3.14
- **Database**: SQLite (development), MySQL-ready
- **Frontend**: Bootstrap 5, vanilla JavaScript
- **File Handling**: Pillow
