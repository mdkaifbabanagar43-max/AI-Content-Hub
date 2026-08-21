import sys
import requests

def run_tests(url: str):
    print(f"Running security tests against: {url}")
    
    payload = {
        "schema_version": 1,
        "job_id": "test_job_canary",
        "user_id": "test_user_canary",
        "project_id": "test_project_canary",
        "blueprint_id": "test_blueprint_canary",
        "test_mode": True
    }
    
    # 1. No auth
    r = requests.post(url, json=payload)
    print(f"No auth -> {r.status_code}")
    
    # 2. Fake auth
    r = requests.post(url, json=payload, headers={"Authorization": "Bearer fake_token"})
    print(f"Fake auth -> {r.status_code}")
    
    # 3. Fake header without auth
    r = requests.post(url, json=payload, headers={"X-CloudTasks-QueueName": "generation-queue"})
    print(f"Fake X-CloudTasks-QueueName -> {r.status_code}")
    
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_security_tests.py <URL>")
        sys.exit(1)
    
    run_tests(sys.argv[1])
