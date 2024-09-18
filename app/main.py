from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Union
import motor.motor_asyncio
from celery_config.result import AsyncResult

# Import Celery and the processing task
from app.celery_config import celery_app
from app.tasks import process_log

app = FastAPI()

# MongoDB connection settings
client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
db = client.log_database
log_collection = db.logs


# Model for JSON log input (for validation)
class LogModel(BaseModel):
    log_data: Union[dict, str]  # Log data can be JSON or plain string


# POST endpoint to receive and store logs
@app.post("/logs")
async def receive_log(log: LogModel, background_tasks: BackgroundTasks):
    """
    Endpoint to receive logs via POST request and process asynchronously using Celery.
    """
    log_data = log.log_data

    # Case 1: JSON log
    if isinstance(log_data, dict):
        # Store the log in MongoDB
        inserted_log = await log_collection.insert_one(log_data)
        log_id = str(inserted_log.inserted_id)

        # Asynchronously process the log (e.g., remove sensitive data)
        background_tasks.add_task(process_log.delay, log_data)

    # Case 2: Non-JSON log (string)
    elif isinstance(log_data, str):
        # Handle non-JSON logs (if necessary, you can expand this later)
        pass

    else:
        raise HTTPException(status_code=400, detail="Invalid log format")

    return {"status": "Log stored and processing", "log_id": log_id}


# Endpoint to check task status
@app.get("/task/{task_id}")
def get_task_status(task_id: str):
    """
    Endpoint to check the status of a Celery background task.
    """
    task_result = AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result if task_result.ready() else None
    }


# Health check route
@app.get("/")
async def root():
    return {"message": "API is operational"}
