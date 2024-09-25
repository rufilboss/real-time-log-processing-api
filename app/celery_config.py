from celery import Celery

# Configure Celery to use Redis as the broker
celery_app = Celery(
    "log_processing",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0",
)

celery_app.conf.update(
    task_routes={
        "tasks.process_log": {"queue": "log_queue"} 
    },
    result_expires=3600,
)

# Define a sample periodic task (optional, for future use)
celery_app.conf.beat_schedule = {
    "sample_task": {
        "task": "tasks.process_log",
        "schedule": 10.0,
    },
}
