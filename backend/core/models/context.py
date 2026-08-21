from typing import Optional, Dict, Any
from pydantic import BaseModel

class GenerationContext(BaseModel):
    user_id: str
    project_id: str
    job_id: str
    metadata: Optional[Dict[str, Any]] = None
    generation_mode: str = "default"
    request_id: Optional[str] = None
