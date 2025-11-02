from celery import Celery
from app.settings import settings

# Configure Celery to use Redis as the broker
celery_app = Celery(
    "log_processing",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Import tasks module to register tasks
import app.tasks  # noqa: F401

celery_app.conf.update(
    result_expires=3600,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Note: Beat schedule disabled by default
# celery_app.conf.beat_schedule = {
#     "sample_task": {
#         "task": "app.tasks.process_log",
#         "schedule": 10.0,
#     },
# }
