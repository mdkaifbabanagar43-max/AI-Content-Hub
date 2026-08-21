from typing import Optional
from pydantic import BaseModel, Field
import datetime
import uuid

class SourceVideoRecord(BaseModel):
    source_video_id: str = Field(default_factory=lambda: f"src_{uuid.uuid4().hex[:8]}")
    user_id: str
    project_id: str
    gcs_uri: str
    filename: str
    size_bytes: int
    duration_seconds: Optional[float] = None
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

class FinalVideoRecord(BaseModel):
    final_video_id: str = Field(default_factory=lambda: f"fv_{uuid.uuid4().hex[:8]}")
    user_id: str
    project_id: str
    source_video_id: str
    source_clone_blueprint_id: str
    source_clone_blueprint_version: int
    production_blueprint_id: str
    production_blueprint_version: int
    output_uri: str
    duration_seconds: float
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    status: str = "COMPLETED"
