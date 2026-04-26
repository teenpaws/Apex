"""
Apex Celery application — task queue configuration.

All Celery workers import `celery_app` from this module.
Beat schedule triggers signal ingestion every 4 hours.

Usage (worker):
    celery -A app.core.celery_app worker --loglevel=info -Q default

Usage (beat scheduler):
    celery -A app.core.celery_app beat --loglevel=info
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "apex",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.ingest_signals",
        "app.workers.classify_signals",
        "app.workers.extract_profile",
    ],
)

celery_app.conf.update(
    # Serialization — always JSON so tasks are human-readable in Redis
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Time zone
    timezone="UTC",
    enable_utc=True,

    # Reliability settings
    task_track_started=True,
    task_acks_late=True,           # ack only after task completes (safe re-queue on crash)
    worker_prefetch_multiplier=1,  # one task at a time per worker (prevents starvation)

    # Priority queues — workers can listen to specific queues
    task_queues={
        "high": {"exchange": "high", "routing_key": "high"},
        "default": {"exchange": "default", "routing_key": "default"},
        "low": {"exchange": "low", "routing_key": "low"},
    },
    task_default_queue="default",

    # Beat schedule: trigger full signal ingestion every 4 hours
    beat_schedule={
        "ingest-signals-every-4-hours": {
            "task": "app.workers.ingest_signals.ingest_all_sources",
            "schedule": 14400.0,  # seconds (4 hours)
            "kwargs": {"user_id": "system"},
        }
    },
)
