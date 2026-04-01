# Deadman Switch

A distributed backend system that monitors user liveness and triggers automated fallback actions when users fail to check in within a configured timeout period.

## Tech Stack

- **Python / FastAPI** — async REST API with session-based auth
- **PostgreSQL** — persistent storage with indexed timestamps and transactional state transitions
- **Celery + Redis** — distributed background watchdog service for scanning expired switches
- **Docker Compose** — multi-service containerized deployment

## Architecture

```
┌────────────┐     ┌───────────┐     ┌────────────┐
│  FastAPI    │────>│ PostgreSQL│<────│  Celery    │
│  (Web)     │     │           │     │  Worker    │
└────────────┘     └───────────┘     └────────────┘
                                           │
┌────────────┐     ┌───────────┐     ┌─────┴──────┐
│  Browser   │────>│  Static   │     │  Celery    │
│            │     │  Files    │     │  Beat      │
└────────────┘     └───────────┘     └────────────┘
                                           │
                                     ┌─────┴──────┐
                                     │   Redis    │
                                     │  (Broker)  │
                                     └────────────┘
```

- **Web** — handles user auth, switch creation, and manual check-ins
- **Celery Beat** — schedules the watchdog task every 60 seconds
- **Celery Worker** — scans for expired switches, transitions state, and sends email notifications
- **Redis** — message broker between Beat and Worker

## How It Works

1. User creates a switch with a configurable timeout period
2. The user must periodically check in before the timer expires
3. A background Celery worker runs every minute to scan all active switches
4. When 25% of time remains, a reminder email is sent
5. If the timeout expires without a check-in, the switch transitions to **triggered** and a notification email is sent
6. Checking in resets the timer and clears the triggered state

## Running with Docker

```bash
docker compose up --build
```

This starts all five services: `web`, `celery-worker`, `celery-beat`, `redis`, and `postgres`.

The app will be available at `http://localhost:8000`.

## Running Locally (without Docker)

Prerequisites: Python 3.13+, PostgreSQL, Redis

```bash
# Install dependencies
pip install .

# Start Redis (if not already running)
redis-server

# Run the API server
uvicorn app.main:app --reload

# Run the Celery worker (separate terminal)
celery -A app.celery_app:celery worker --loglevel=info

# Run the Celery beat scheduler (separate terminal)
celery -A app.celery_app:celery beat --loglevel=info
```

## Environment Variables

| Variable | Description |
|---|---|
| `DB_USER` | PostgreSQL username |
| `DB_PASSWORD` | PostgreSQL password |
| `DB_HOST` | PostgreSQL host |
| `DB_PORT` | PostgreSQL port |
| `DB_NAME` | PostgreSQL database name |
| `DATABASE_URL` | Full PostgreSQL connection string (overrides individual DB vars) |
| `SECRET_KEY` | Session signing key |
| `REDIS_URL` | Redis connection string (default: `redis://localhost:6379/0`) |
| `SMTP_SERVER` | SMTP server address |
| `SMTP_PORT` | SMTP port |
| `SMTP_USERNAME` | SMTP username |
| `SMTP_PASSWORD` | SMTP password |
| `EMAIL_FROM` | Sender email address |
| `BASE_URL` | Public URL for email links (default: `http://localhost:8000`) |

## Project Structure

```
app/
  main.py           # FastAPI application and routes
  models.py         # SQLAlchemy models (User, Switch, PasswordResetToken)
  database.py       # Database engine and session management
  celery_app.py     # Celery instance and beat schedule configuration
  tasks.py          # Background watchdog task
  email_service.py  # SMTP email notifications
templates/          # Jinja2 HTML templates
static/css/         # Stylesheets
Dockerfile
docker-compose.yml
```
