import sys
import os
from datetime import datetime

# Add the parent directory to the python path so we can import from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.repositories.job_repo import GenerationJobRepository
from core.models.job import GenerationJob

def setup():
    user_id = "test_user_canary"
    project_id = "test_project_canary"
    blueprint_id = "test_blueprint_canary"
    job_id = "test_job_canary"

    # We need to reserve credits, so the user needs some credits.
    # Actually, we can just create the document manually with QUEUED state to bypass credit checks for this test,
    # OR we can give the user credits. Let's just create it as QUEUED manually.
    
    repo = GenerationJobRepository()
    
    # Give user some credits
    user_ref = repo._get_user_ref(user_id)
    user_ref.set({"credits": 100, "reserved_credits": 0})
    
    # We will use try_start_job in the worker, which requires it to be QUEUED.
    job = GenerationJob(
        user_id=user_id,
        project_id=project_id,
        blueprint_id=blueprint_id,
        job_id=job_id,
        status="QUEUED",
        reserved_credits=10
    )
    repo.save(job)
    
    from core.repositories.blueprint_repo import BlueprintRepository
    from core.models.blueprint import ProductionBlueprint
    bp_repo = BlueprintRepository()
    bp = ProductionBlueprint(
        blueprint_id=blueprint_id,
        project_id=project_id,
        user_id=user_id,
        title="Canary Test",
        concept="Canary",
        genre="Test",
        target_duration_seconds=10,
        status="APPROVED",
        timeline=None
    )
    bp_repo.save(user_id, bp)
    
    print(f"Set up job {job_id} and blueprint for {user_id}")

if __name__ == "__main__":
    setup()
