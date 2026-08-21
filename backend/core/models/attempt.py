from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class GenerationAttempt(BaseModel):
    attempt_id: str
    project_id: str
    scene_id: str
    attempt_number: int
    prompt: str
    reference_uri: Optional[str] = None
    provider: str = "Google Vertex AI"
    model: str = "veo-3.1-fast-generate-001"
    region: Optional[str] = "us-central1"
    target_duration: Optional[float] = None
    actual_duration: Optional[float] = None
    audio_duration: Optional[float] = None
    output_uri: Optional[str] = None
    output_path: Optional[str] = None
    quality_review_id: Optional[str] = None
    quality_review: Optional[dict] = None
    rejection_reason: Optional[str] = None
    error_category: Optional[str] = None
    score: Optional[float] = None
    status: str = "pending"  # "REQUESTED", "IN_PROGRESS", "COMPLETED", "FAILED", "REJECTED"
    blueprint_id: Optional[str] = None
    blueprint_version: Optional[int] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Phase 8F & 8G.1 Reference Conditioning & Operation State Telemetry
    reference_requested: bool = False
    reference_source: Optional[str] = None  # "PROJECT_BIBLE", "CHARACTER_ASSET", "CACHE", "GENERATED_ASSET", "FALLBACK"
    reference_asset_id: Optional[str] = None
    reference_generation_attempted: bool = False
    reference_generation_status: Optional[str] = None  # "SUCCESS", "FAILED", "SKIPPED", "NOT_REQUESTED"
    reference_validation_status: Optional[str] = None  # "VALID", "INVALID", "BYPASSED"
    reference_failure_reason: Optional[str] = None
    fallback_mode: Optional[str] = None  # "PROMPT_ONLY", "CANONICAL_FALLBACK", None
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    
    # Granular per-operation lifecycle record mapping
    operation_states: Dict[str, Any] = Field(default_factory=dict)
