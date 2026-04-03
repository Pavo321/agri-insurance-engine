from celery import Celery
from celery.schedules import crontab

from config.settings import settings

celery_app = Celery(
    "agri_insurance",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "workers.tasks.ingest_weather",
        "workers.tasks.ingest_ndvi",
        "workers.tasks.evaluate_rules",
        "workers.tasks.dispatch_payout",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_acks_late=True,             # re-queue on worker crash
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,    # fair dispatch for long-running tasks
    beat_schedule={
        # IMD weather: every 30 minutes
        "ingest-imd-weather": {
            "task": "workers.tasks.ingest_weather.fetch_imd_maharashtra",
            "schedule": crontab(minute="*/30"),
        },
        # ISRO NDVI: daily at 03:00 IST
        "ingest-bhuvan-ndvi": {
            "task": "workers.tasks.ingest_ndvi.fetch_ndvi_maharashtra",
            "schedule": crontab(hour=3, minute=0),
        },
        # Rules evaluation: every hour
        "evaluate-trigger-rules": {
            "task": "workers.tasks.evaluate_rules.evaluate_all_farms",
            "schedule": crontab(minute=0),
        },
        # Poll PENDING payouts: every 10 minutes
        "poll-pending-payouts": {
            "task": "workers.tasks.dispatch_payout.poll_pending_payouts",
            "schedule": crontab(minute="*/10"),
        },
    },
)
