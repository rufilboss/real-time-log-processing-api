from celery.utils.log import get_task_logger
from app.celery_config import celery_app 
import re

# Initialize Celery logger
logger = get_task_logger(__name__)

# Example sensitive information patterns to filter (emails, phone numbers)
EMAIL_REGEX = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
PHONE_REGEX = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'

# Celery task to process and filter logs (e.g., remove sensitive info)
@celery_app.task(name="tasks.process_log")
def process_log(log_data: dict) -> dict:
    """
    Task to process the log data by removing sensitive information such as emails and phone numbers.

    :param log_data: The original log data
    :return: Processed log data with sensitive info removed
    """
    logger.info("Starting log processing task.")
    
    # Remove sensitive information from log fields
    for key, value in log_data.items():
        if isinstance(value, str):
            log_data[key] = re.sub(EMAIL_REGEX, "[REDACTED_EMAIL]", value)
            log_data[key] = re.sub(PHONE_REGEX, "[REDACTED_PHONE]", value)

    logger.info("Log processing task completed.")
    return log_data
