from fastapi import FastAPI, BackgroundTasks, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Union
import motor.motor_asyncio
from app.celery_config import celery_app
from app.tasks import process_log 
from celery.result import AsyncResult
from app.settings import settings
from prometheus_fastapi_instrumentator import Instrumentator
import logging
import json

app = FastAPI(title=settings.app_name)

# Templates for UI
import os
template_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=template_dir)

# MongoDB connection (database extracted from URI or default)
client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongo_uri)
# Extract database name from URI or use default
db_name = settings.mongo_uri.split("/")[-1].split("?")[0] if "/" in settings.mongo_uri else "log_database"
db = client[db_name] if db_name else client.log_database
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
        # Convert to JSON-serializable format for Celery (remove MongoDB ObjectId)
        log_data_for_task = json.loads(json.dumps(log_data, default=str))
        log_data_for_task["_id"] = log_id
        try:
            task = celery_app.send_task("app.tasks.process_log", args=[log_data_for_task])
            task_id = task.id
        except Exception as e:
            logging.error(f"Failed to send Celery task: {e}")
            task_id = None

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


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Main dashboard UI"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/ui/submit")
async def ui_submit_form():
    """Redirect for GET requests to submit"""
    return {"message": "Use POST to submit logs"}


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


# UI Routes
@app.post("/ui/submit", response_class=HTMLResponse)
async def ui_submit(request: Request, log_data: str = Form(...)):
    """Submit log from UI form"""
    try:
        # Parse JSON from form
        log_dict = json.loads(log_data)
        
        # Store in MongoDB
        inserted_log = await log_collection.insert_one(log_dict)
        log_id = str(inserted_log.inserted_id)
        
        # Start Celery task (ensure JSON serializable)
        log_dict_for_task = json.loads(json.dumps(log_dict, default=str))
        log_dict_for_task["_id"] = log_id
        task = celery_app.send_task("app.tasks.process_log", args=[log_dict_for_task])
        task_id = task.id
        
        return templates.TemplateResponse(
            "result_message.html",
            {
                "request": request,
                "success": True,
                "message": "Log submitted successfully",
                "log_id": log_id,
                "task_id": task_id
            }
        )
    except json.JSONDecodeError:
        return templates.TemplateResponse(
            "result_message.html",
            {
                "request": request,
                "success": False,
                "message": "Invalid JSON format"
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "result_message.html",
            {
                "request": request,
                "success": False,
                "message": f"Error: {str(e)}"
            }
        )


@app.get("/ui/logs", response_class=HTMLResponse)
async def ui_logs(request: Request):
    """Get recent logs for UI"""
    try:
        # Fetch last 10 logs
        cursor = log_collection.find().sort("_id", -1).limit(10)
        logs = await cursor.to_list(length=10)
        
        # Convert ObjectId to string and prepare JSON strings for display
        logs_with_json = []
        for log in logs:
            if "_id" in log:
                log["_id"] = str(log["_id"])
            log_json = json.dumps(log, indent=2, default=str)
            logs_with_json.append({"log": log, "log_json": log_json})
        
        return templates.TemplateResponse("logs_list.html", {"request": request, "logs": logs_with_json})
    except Exception as e:
        return templates.TemplateResponse(
            "logs_list.html",
            {"request": request, "logs": None, "error": str(e)}
        )


@app.get("/ui/task-status", response_class=HTMLResponse)
async def ui_task_status(request: Request, task_id: str):
    """Get task status for UI"""
    try:
        task_result = AsyncResult(task_id, app=celery_app)
        
        if task_result is None:
            return templates.TemplateResponse(
                "task_status.html",
                {"request": request, "task": None}
            )
        
        result = task_result.result if task_result.ready() else None
        task_result_json = json.dumps(result, indent=2, default=str) if result else None
        
        task_data = {
            "task_id": task_id,
            "status": task_result.status,
            "result": result,
            "result_json": task_result_json
        }
        
        return templates.TemplateResponse(
            "task_status.html",
            {"request": request, "task": task_data}
        )
    except Exception as e:
        return templates.TemplateResponse(
            "task_status.html",
            {"request": request, "task": None, "error": str(e)}
        )
