"""Celery application configuration and beat schedule setup."""

from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "resolveai_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    worker_prefetch_multiplier=1,
)

# Celery Beat Periodic Schedule
celery_app.conf.beat_schedule = {
    "evaluate-sla-breaches-every-minute": {
        "task": "app.workers.tasks.check_all_sla_breaches",
        "schedule": 60.0,  # Every 60 seconds
    },
}
