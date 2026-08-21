import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

from core.models.source_analysis import HookAnalysis, CTAAnalysis, SourceAudioProfile, SourceVisualStyle

class CloneShot(BaseModel):
    shot_number: int
    source_start_seconds: float
    source_end_seconds: float
    duration_seconds: float
    shot_type: str = Field(description="Wide, Medium, Close-up, etc.")
    camera_motion: str = Field(description="Static, Pan, Tracking, etc.")
    framing: Optional[str] = Field(None)
    lens_description: Optional[str] = Field(None)
    camera_angle: Optional[str] = Field(None)
    composition: Optional[str] = Field(None)
    visual_action: str
    transition: Optional[str] = Field(None)

class CloneSceneBlueprint(BaseModel):
    scene_id: str
    scene_number: int
    source_start_seconds: float
    source_end_seconds: float
    source_duration_seconds: float
    narrative_purpose: str
    visual_action: str
    dialogue_intent: Optional[str] = Field(None)
    emotion: str
    pacing: str
    shot_sequence: List[CloneShot] = Field(default_factory=list)
    character_roles: List[str] = Field(default_factory=list)
    location_summary: Optional[str] = Field(None)
    prop_summary: Optional[str] = Field(None)
    lighting_summary: Optional[str] = Field(None)
    transition: Optional[str] = Field(None)
    audio_structure: Optional[str] = Field(None)

class NarrativeBeat(BaseModel):
    type: Literal["HOOK", "SETUP", "CONFLICT", "ESCALATION", "DISCOVERY", "TWIST", "RESOLUTION", "CTA", "OTHER"]
    start_seconds: float
    end_seconds: float
    description: str
    importance: Literal["HIGH", "MEDIUM", "LOW"] = Field(default="MEDIUM")

class PacingProfile(BaseModel):
    overall_intensity: str
    average_shot_duration: float
    fastest_shot_duration: float
    slowest_shot_duration: float
    scene_count: int
    shot_count: int
    rhythm_description: str

class CloneBlueprint(BaseModel):
    clone_blueprint_id: str
    source_video_id: str
    project_id: str
    user_id: str
    clone_blueprint_version: int = Field(default=1)
    source_analysis_version: str
    title: str
    source_duration_seconds: float
    target_duration_seconds: float
    aspect_ratio: str
    hook: HookAnalysis
    narrative_structure: List[NarrativeBeat] = Field(default_factory=list)
    pacing_profile: PacingProfile
    visual_style_profile: SourceVisualStyle
    audio_profile: SourceAudioProfile
    cta_structure: CTAAnalysis
    scenes: List[CloneSceneBlueprint] = Field(default_factory=list)
    
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    status: Literal["DRAFT", "READY_FOR_TRANSFORMATION", "SUPERSEDED"] = Field(default="DRAFT")
    analyzer_version: str = Field(default="1.0.0")
