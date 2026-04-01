import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery = Celery(
    "deadman_switch",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks"],
)

celery.conf.beat_schedule = {
    "check-switches-every-minute": {
        "task": "app.tasks.check_switches_and_send_emails",
        "schedule": 60.0,
    },
}
celery.conf.timezone = "UTC"
