from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime, timezone
import uuid

class GenerationJob(BaseModel):
    job_id: str = Field(default_factory=lambda: f"job_{uuid.uuid4().hex[:12]}")
    user_id: str
    project_id: str
    blueprint_id: str
    status: Literal["QUEUED", "RUNNING", "COMPLETED", "FAILED"] = "QUEUED"
    
    # Credit reservation
    reserved_credits: int = 0
    
    # Observability
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    is_retryable: bool = False
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
