"""
Celery background tasks — watchdog service that scans for expired switches
and triggers fallback actions (email notifications).
"""
import os
from datetime import datetime, timedelta
from app.celery_app import celery
from app.database import SessionLocal
from app.models import Switch
from app.email_service import send_trigger_notification, send_reminder_notification


@celery.task(name="app.tasks.check_switches_and_send_emails")
def check_switches_and_send_emails():
    """Periodic task: scan all active switches and send reminder/trigger emails."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        active_switches = db.query(Switch).filter_by(status="active").all()
        base_url = os.environ.get("BASE_URL", "http://localhost:8000")
        dashboard_url = f"{base_url}/dashboard"

        for switch in active_switches:
            next_trigger_time = switch.last_checkin + timedelta(seconds=switch.timeout_period)
            time_remaining = (next_trigger_time - now).total_seconds()

            # Switch has expired — transition to triggered state
            if time_remaining <= 0 and not switch.trigger_email_sent:
                switch.status = "triggered"
                switch.trigger_email_sent = True
                db.commit()
                send_trigger_notification(switch.user.email, switch, dashboard_url)
                print(f"[CELERY] Trigger email sent for switch {switch.id}")

            # Send reminder when 25% time remaining (or <1 hour for long timeouts)
            elif time_remaining > 0 and not switch.reminder_sent:
                percent_remaining = (time_remaining / switch.timeout_period) * 100
                if percent_remaining <= 25 or (time_remaining <= 3600 and switch.timeout_period > 3600):
                    send_reminder_notification(switch.user.email, switch, int(time_remaining), dashboard_url)
                    switch.reminder_sent = True
                    db.commit()
                    print(f"[CELERY] Reminder email sent for switch {switch.id}")
    finally:
        db.close()
