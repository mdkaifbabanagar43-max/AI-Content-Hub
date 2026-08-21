import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.repositories.job_repo import GenerationJobRepository

def check():
    user_id = "test_user_canary"
    project_id = "test_project_canary"
    blueprint_id = "test_blueprint_canary"
    job_id = "test_job_canary"

    repo = GenerationJobRepository()
    job = repo.get(user_id, project_id, blueprint_id, job_id)
    
    if not job:
        print("Job not found.")
        return
        
    print(f"Job Status: {job.status}")
    print(f"Reserved Credits: {job.reserved_credits}")
    print(f"Updated At: {job.updated_at}")
    
    user_ref = repo._get_user_ref(user_id)
    user_snap = user_ref.get()
    if user_snap.exists:
        data = user_snap.to_dict()
        print(f"User Credits: {data.get('credits')}")
        print(f"User Reserved Credits: {data.get('reserved_credits')}")

if __name__ == "__main__":
    check()
