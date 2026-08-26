import os
import json
import logging
from config import (
    CLOUD_TASKS_PROJECT, 
    CLOUD_TASKS_LOCATION, 
    CLOUD_TASKS_QUEUE_NAME,
    SERVICE_ACCOUNT_EMAIL,
    WORKER_URL,
    WORKER_AUDIENCE
)

# Initialize client lazily so local tests without credentials don't immediately crash
_client = None

def _get_client():
    global _client
    if _client is None:
        from google.cloud import tasks_v2
        _client = tasks_v2.CloudTasksClient()
    return _client

def enqueue_generation_task(user_id: str, project_id: str, blueprint_id: str, job_id: str):
    """
    Enqueues a job to Google Cloud Tasks for durable asynchronous generation.
    """
    # For local testing without GCP credentials, we can bypass the real queue
    # Check if we are running under pytest (commonly sets PYTEST_CURRENT_TEST)
    if "PYTEST_CURRENT_TEST" in os.environ or os.environ.get("MOCK_CLOUD_TASKS") == "1":
        logging.info(f"[MOCK] Enqueuing task for job {job_id}")
        return True

    client = _get_client()

    
    parent = client.queue_path(CLOUD_TASKS_PROJECT, CLOUD_TASKS_LOCATION, CLOUD_TASKS_QUEUE_NAME)
    
    # Deterministic task name for exact deduplication by Cloud Tasks
    # Task names can contain letters, numbers, hyphens.
    clean_job_id = job_id.replace("_", "-")
    task_name = f"{parent}/tasks/generation-{clean_job_id}"
    
    payload = {
        "schema_version": 1,
        "job_id": job_id,
        "user_id": user_id,
        "project_id": project_id,
        "blueprint_id": blueprint_id
    }
    
    task = {
        "name": task_name,
        "http_request": {
            "http_method": "POST",
            "url": WORKER_URL,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(payload).encode(),
            "oidc_token": {
                "service_account_email": SERVICE_ACCOUNT_EMAIL,
                "audience": WORKER_AUDIENCE
            }
        }
    }
    
    try:
        response = client.create_task(
            request={"parent": parent, "task": task}
        )
        logging.info(f"Enqueued Cloud Task: {response.name}")
        return True
    except Exception as e:
        if type(e).__name__ == "AlreadyExists":
            logging.info(f"Task {task_name} already exists. Ignoring duplicate enqueue.")
            return True
        logging.error(f"Failed to enqueue Cloud Task {task_name}: {e}")
        return False
