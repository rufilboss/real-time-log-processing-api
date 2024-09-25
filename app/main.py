from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Union
from bson import ObjectId
import motor.motor_asyncio
from app.celery_config import celery_app
from app.tasks import process_log 
from celery.result import AsyncResult
# from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# MongoDB connection
client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://mongo:27017")
db = client.log_database
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
        # Handle non-JSON logs (if necessary, you can expand this later)
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
# @app.get("/task/{task_id}")
# def get_task_status(task_id: str):
#     """
#     Endpoint to check the status of a Celery background task.
#     """
#     task_result = AsyncResult(task_id)
#     return {
#         "task_id": task_id,
#         "status": task_result.status,
#         "result": task_result.result if task_result.ready() else None
#     }
    
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

# Health check route
@app.get("/")
async def root():
    return {"message": "API is operational"}
