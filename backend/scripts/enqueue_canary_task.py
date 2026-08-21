import sys
import os
import json
from google.cloud import tasks_v2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PROJECT_ID, REGION, CLOUD_TASKS_QUEUE, SERVICE_ACCOUNT_EMAIL

def enqueue_canary_task(url: str):
    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(PROJECT_ID, REGION, CLOUD_TASKS_QUEUE)
    
    payload = {
        "schema_version": 1,
        "job_id": "test_job_canary",
        "user_id": "test_user_canary",
        "project_id": "test_project_canary",
        "blueprint_id": "test_blueprint_canary",
        "test_mode": True
    }
    
    task_id = "generation-test_job_canary"
    task_name = client.task_path(PROJECT_ID, REGION, CLOUD_TASKS_QUEUE, task_id)
    
    task = {
        "name": task_name,
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": url,
            "headers": {"Content-type": "application/json"},
            "body": json.dumps(payload).encode(),
            "oidc_token": {
                "service_account_email": SERVICE_ACCOUNT_EMAIL,
                "audience": url
            }
        }
    }
    
    # In case the task exists from a previous run, delete it first
    try:
        client.delete_task(name=task_name)
        print("Deleted existing test task.")
    except Exception:
        pass
        
    response = client.create_task(request={"parent": parent, "task": task})
    print(f"Enqueued task: {response.name}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python enqueue_canary_task.py <CANARY_URL>")
        sys.exit(1)
    
    enqueue_canary_task(sys.argv[1])
