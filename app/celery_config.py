import celery
from celery import Celery

# Configure Celery to use Redis as the broker
celery_app = Celery(
    "log_processing",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

celery_app.conf.update(
    task_routes={
        "tasks.process_log": {"queue": "log_queue"}  # Task routing for log processing
    },
    result_expires=3600,
)

# Define a sample periodic task (optional, for future use)
celery_app.conf.beat_schedule = {
    "sample_task": {
        "task": "tasks.process_log",
        "schedule": 10.0,  # Schedule every 10 seconds
    },
}
