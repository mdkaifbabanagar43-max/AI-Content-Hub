from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import os
import datetime

class OperationStatus(str, Enum):
    NOT_REQUESTED = "NOT_REQUESTED"
    REQUESTED = "REQUESTED"
    STARTED = "STARTED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    FALLBACK_USED = "FALLBACK_USED"

class ErrorCategory(str, Enum):
    NONE = "NONE"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    INVALID_REQUEST = "INVALID_REQUEST"
    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT = "TIMEOUT"
    REFERENCE_GENERATION_FAILED = "REFERENCE_GENERATION_FAILED"
    REFERENCE_VALIDATION_FAILED = "REFERENCE_VALIDATION_FAILED"
    VEO_GENERATION_FAILED = "VEO_GENERATION_FAILED"
    AUDIO_GENERATION_FAILED = "AUDIO_GENERATION_FAILED"
    LIPSYNC_FAILED = "LIPSYNC_FAILED"
    QUALITY_REJECTED = "QUALITY_REJECTED"
    TIMELINE_FAILED = "TIMELINE_FAILED"
    ASSEMBLY_FAILED = "ASSEMBLY_FAILED"
    STORAGE_FAILED = "STORAGE_FAILED"
    UNAUTHORIZED_FALLBACK = "UNAUTHORIZED_FALLBACK"

class JobStatus(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class OperationRecord(BaseModel):
    operation_name: str
    scene_id: Optional[str] = None
    attempt_id: Optional[str] = None
    required: bool = True
    status: OperationStatus = OperationStatus.NOT_REQUESTED
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    region: Optional[str] = None
    error_type: ErrorCategory = ErrorCategory.NONE
    error_message: Optional[str] = None
    fallback_used: bool = False
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None
    fallback_reason: Optional[str] = None
    output_reference: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class FallbackPolicyRule(BaseModel):
    operation: str
    primary_provider: str
    primary_model: str
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None
    allowed: bool = False
    trigger_conditions: List[str] = Field(default_factory=list)
    max_attempts: int = 1
    telemetry_required: bool = True

# Central Explicit Fallback Policies (Fail-closed by default for critical operations)
CENTRAL_FALLBACK_POLICIES: Dict[str, FallbackPolicyRule] = {
    "character_reference_generation": FallbackPolicyRule(
        operation="character_reference_generation",
        primary_provider="Google Vertex AI",
        primary_model="gemini-2.5-flash-image",
        fallback_provider="Google Vertex AI",
        fallback_model="imagen-3.0-generate-002",
        allowed=True, # Model cascade within provider is allowed if configured
        trigger_conditions=["MODEL_NOT_FOUND", "PROVIDER_UNAVAILABLE"],
        max_attempts=3,
        telemetry_required=True
    ),
    "veo_generation": FallbackPolicyRule(
        operation="veo_generation",
        primary_provider="Google Vertex AI",
        primary_model="veo-3.1-fast-generate-001",
        allowed=False, # No unauthorized model substitution
        trigger_conditions=[],
        max_attempts=1,
        telemetry_required=True
    ),
    "elevenlabs_voiceover": FallbackPolicyRule(
        operation="elevenlabs_voiceover",
        primary_provider="ElevenLabs",
        primary_model="eleven_multilingual_v2",
        allowed=False, # No silent dropping of audio
        trigger_conditions=[],
        max_attempts=1,
        telemetry_required=True
    ),
    "synclabs_lipsync": FallbackPolicyRule(
        operation="synclabs_lipsync",
        primary_provider="SyncLabs",
        primary_model="lipsync-2",
        fallback_provider="MoviePy Mux",
        fallback_model="direct_audio_mux",
        allowed=False, # Unauthorized fallback forbidden when lip-sync is required
        trigger_conditions=["EXPLICIT_OPTIONAL_LIPSYNC_CONFIGURED"],
        max_attempts=1,
        telemetry_required=True
    ),
    "timeline_normalization": FallbackPolicyRule(
        operation="timeline_normalization",
        primary_provider="MoviePy/FFmpeg",
        primary_model="timeline_normalizer",
        allowed=False, # No silent skipping of normalization
        trigger_conditions=[],
        max_attempts=1,
        telemetry_required=True
    )
}

class ExecutionCertificate(BaseModel):
    job_id: str
    project_id: str
    total_scenes_expected: int
    total_scenes_generated: int
    all_scenes_approved: bool = False
    timeline_validated: bool = False
    normalized_scene_count: int = 0
    final_mp4_path: Optional[str] = None
    final_mp4_size_bytes: int = 0
    final_duration: float = 0.0
    target_duration: float = 0.0
    duration_within_tolerance: bool = False
    final_upload_uri: Optional[str] = None
    certified: bool = False
    certification_errors: List[str] = Field(default_factory=list)
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

def verify_execution_certificate(
    job_id: str,
    project_id: str,
    expected_scenes_count: int,
    generated_scenes_count: int,
    all_scenes_approved: bool,
    timeline_validated: bool,
    normalized_scene_count: int,
    final_mp4_path: Optional[str],
    final_duration: float,
    target_duration: float,
    final_upload_uri: Optional[str],
    operation_records: Optional[List[OperationRecord]] = None,
    duration_tolerance_seconds: float = 5.0
) -> ExecutionCertificate:
    """
    Validates all production invariants before granting COMPLETED status.
    Strictly fail-closed: if any check fails, certified = False.
    """
    errors: List[str] = []

    if expected_scenes_count <= 0:
        errors.append("Invalid expected scenes count (0 or negative)")

    if generated_scenes_count != expected_scenes_count:
        errors.append(f"Scene count mismatch: expected {expected_scenes_count}, generated {generated_scenes_count}")

    if not all_scenes_approved:
        errors.append("Not all scenes passed QualityReviewer acceptance")

    if not timeline_validated:
        errors.append("TimelineBuilder validation did not pass")

    if normalized_scene_count != expected_scenes_count:
        errors.append(f"Normalized scene count mismatch: expected {expected_scenes_count}, got {normalized_scene_count}")

    mp4_size = 0
    if not final_mp4_path or not os.path.exists(final_mp4_path):
        errors.append(f"Final MP4 file missing on disk: {final_mp4_path}")
    else:
        try:
            mp4_size = os.path.getsize(final_mp4_path)
            if mp4_size == 0:
                errors.append("Final MP4 file has 0 bytes")
        except Exception as e:
            errors.append(f"Cannot read final MP4 size: {e}")

    # Check duration tolerance
    dur_ok = True
    if target_duration > 0 and final_duration > 0:
        if abs(final_duration - target_duration) > max(duration_tolerance_seconds, target_duration * 0.3):
            # If duration drifted heavily
            errors.append(f"Final duration ({final_duration:.2f}s) exceeded tolerance for target ({target_duration:.2f}s)")
            dur_ok = False

    if not final_upload_uri or not (final_upload_uri.startswith("gs://") or final_upload_uri.startswith("http")):
        errors.append(f"Invalid final upload URI: {final_upload_uri}")

    # Inspect all required operation records
    if operation_records:
        for op in operation_records:
            if op.required:
                if op.status in (OperationStatus.FAILED, OperationStatus.SKIPPED):
                    errors.append(f"Required operation '{op.operation_name}' failed or skipped: {op.error_message or op.status}")
                elif op.status in (OperationStatus.REQUESTED, OperationStatus.STARTED):
                    errors.append(f"Required operation '{op.operation_name}' incomplete (status={op.status})")
                elif op.status == OperationStatus.FALLBACK_USED and not op.fallback_used:
                    errors.append(f"Unauthorized fallback on '{op.operation_name}'")

    is_certified = (len(errors) == 0)

    return ExecutionCertificate(
        job_id=job_id,
        project_id=project_id,
        total_scenes_expected=expected_scenes_count,
        total_scenes_generated=generated_scenes_count,
        all_scenes_approved=all_scenes_approved,
        timeline_validated=timeline_validated,
        normalized_scene_count=normalized_scene_count,
        final_mp4_path=final_mp4_path,
        final_mp4_size_bytes=mp4_size,
        final_duration=final_duration,
        target_duration=target_duration,
        duration_within_tolerance=dur_ok,
        final_upload_uri=final_upload_uri,
        certified=is_certified,
        certification_errors=errors
    )

