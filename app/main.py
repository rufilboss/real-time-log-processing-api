from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Union
import motor.motor_asyncio
from app.celery_config import celery_app
from app.tasks import process_log 
from celery.result import AsyncResult
from app.settings import settings
from prometheus_fastapi_instrumentator import Instrumentator
import logging

app = FastAPI(title=settings.app_name)

# MongoDB connection (database extracted from URI or default)
client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongo_uri)
db = client.get_default_database() if client.get_default_database() else client.log_database
log_collection = db.logs

# Model for JSON log input (for validation)
class LogModel(BaseModel):
    log_data: Union[dict, str]  # Log data can be JSON or plain string

# # POST endpoint to receive and store logs
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

        # Start Celery task asynchronously and get the task_id
        log_data["_id"] = log_id 
        task = process_log.delay(log_data)
        task_id = task.id 

        # Add the task to background processing
        background_tasks.add_task(task.get)

    # Case 2: Non-JSON log (string)
    elif isinstance(log_data, str):
        task_id = None
        log_id = None

    else:
        raise HTTPException(status_code=400, detail="Invalid log format")

    # Return the task_id along with the log_id
    return {
        "status": "Log stored and processing...", 
        "log_id": log_id, 
        "task_id": task_id
    }

# Endpoint to check task status 
@app.get("/task/{task_id}")
def get_task_status(task_id: str):
    """
    Endpoint to check the status of a Celery background task.
    """
    task_result = AsyncResult(task_id, app=celery_app)
    
    if task_result is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result if task_result.ready() else None
    }

# Instrumentation: expose Prometheus metrics at /metrics
Instrumentator().instrument(app).expose(app)


@app.get("/")
async def root():
    return {"message": "API is operational", "app": settings.app_name}


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/readyz")
async def readyz():
    # Quick readiness check by pinging Redis via Celery broker URL parse is heavy; keep simple
    # and verify Mongo driver is initialized
    try:
        await db.command("ping")
    except Exception:
        raise HTTPException(status_code=503, detail="Mongo not ready")
    return {"status": "ready"}
