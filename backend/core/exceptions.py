from typing import Optional, Dict, Any

class CanonicalPipelineException(Exception):
    def __init__(self, message: str, error_type: str = "PIPELINE_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.details = details or {}

class CharacterReferenceError(CanonicalPipelineException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_type="REFERENCE_GENERATION_FAILED", details=details)

class ReferenceValidationError(CanonicalPipelineException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_type="REFERENCE_VALIDATION_FAILED", details=details)

class VeoGenerationError(CanonicalPipelineException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_type="VEO_GENERATION_FAILED", details=details)

class AudioGenerationError(CanonicalPipelineException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_type="AUDIO_GENERATION_FAILED", details=details)

class LipSyncError(CanonicalPipelineException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_type="LIPSYNC_FAILED", details=details)

class QualityReviewError(CanonicalPipelineException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_type="QUALITY_REJECTED", details=details)

class TimelineExecutionException(CanonicalPipelineException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_type="TIMELINE_FAILED", details=details)

class AssemblyException(CanonicalPipelineException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_type="ASSEMBLY_FAILED", details=details)
