from typing import List, Optional, Literal, Any, Dict
from pydantic import BaseModel, Field, field_validator
import datetime

from core.models.source_analysis import SourceVisualStyle

class CameraDirection(BaseModel):
    shot_type: Optional[str] = None
    lens: Optional[str] = None
    camera_motion: Optional[str] = None
    angle: Optional[str] = None
    framing: Optional[str] = None
    depth_of_field: Optional[str] = None
    lighting: Optional[str] = None

class DialogueLine(BaseModel):
    character_id: str = "char_lead_1"
    voice_id: str = "default_voice"
    text: str = ""
    emotion: Optional[str] = "neutral"
    delivery_style: Optional[str] = "natural"
    estimated_duration_seconds: float = 3.0

class ContinuityRequirement(BaseModel):
    asset_id: str
    required_state: str
    priority: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"

class AudioStrategy(BaseModel):
    primary_voice_id: Optional[str] = None
    music_mood: Optional[str] = None
    sfx_density: Optional[str] = None

class QualityStrategy(BaseModel):
    global_priority: Literal["CHARACTER_CRITICAL", "CONTINUITY_CRITICAL", "ACTION_CRITICAL", "VISUAL_QUALITY_CRITICAL", "BALANCED"] = "BALANCED"
    max_retries: int = 1

class GenerationStrategy(BaseModel):
    preferred_video_model: str = "veo-3.1"
    preferred_resolution: str = "1080p"
    target_fps: int = 30
    reference_policy: Literal["SINGLE_PRIMARY"] = "SINGLE_PRIMARY"
    chunking_strategy: str = "8s_chunks"
    quality_threshold: float = 8.0

class SceneBlueprint(BaseModel):
    scene_id: str
    scene_number: int = 1
    narrative_purpose: str = "Scene narrative"
    estimated_duration_seconds: float = 5.0
    character_ids: List[str] = Field(default_factory=list)
    location_id: Optional[str] = None
    prop_ids: List[str] = Field(default_factory=list)
    dialogue: List[DialogueLine] = Field(default_factory=list)
    emotion: Optional[str] = None
    action: Optional[str] = None
    camera: Optional[CameraDirection] = None
    environment: Optional[str] = None
    continuity_requirements: List[ContinuityRequirement] = Field(default_factory=list)
    primary_reference_asset_id: Optional[str] = None
    transition: Optional[str] = "CUT"
    scene_quality_priority: Literal["CHARACTER_CRITICAL", "CONTINUITY_CRITICAL", "ACTION_CRITICAL", "VISUAL_QUALITY_CRITICAL", "BALANCED"] = "BALANCED"
    
    # Unified LipSync Policy
    use_lip_sync: Optional[bool] = None
    allow_lip_sync_fallback: Optional[bool] = None
    
    # Storyboard & Shot Reference Pack
    storyboard_shots: List[Dict[str, Any]] = Field(default_factory=list)
    shot_reference_pack: Optional[Dict[str, Any]] = None

    @field_validator("dialogue", mode="before")
    @classmethod
    def normalize_dialogue(cls, v):
        if isinstance(v, str):
            if not v.strip():
                return []
            return [{"text": v.strip(), "character_id": "char_lead_1", "voice_id": "default_voice", "estimated_duration_seconds": 3.0}]
        if isinstance(v, list):
            res = []
            for item in v:
                if isinstance(item, str):
                    res.append({"text": item.strip(), "character_id": "char_lead_1", "voice_id": "default_voice", "estimated_duration_seconds": 3.0})
                else:
                    res.append(item)
            return res
        return v

class ProductionBlueprint(BaseModel):
    project_id: str
    blueprint_version: int = 1
    blueprint_id: str = Field(default_factory=lambda: "")
    source_clone_blueprint_id: Optional[str] = None
    source_clone_blueprint_version: Optional[int] = None
    title: str
    concept: str
    genre: str
    target_duration_seconds: float
    aspect_ratio: str = "9:16"
    visual_style_id: Optional[str] = None
    visual_style_profile: Optional[SourceVisualStyle] = None
    authoritative_art_style: Optional[str] = None
    authoritative_character_design: Optional[str] = None
    visual_identity_pack_id: Optional[str] = None
    required_character_ids: List[str] = Field(default_factory=list)
    required_location_ids: List[str] = Field(default_factory=list)
    required_prop_ids: List[str] = Field(default_factory=list)
    global_continuity_rules: Optional[str] = None
    audio_strategy: Optional[AudioStrategy] = None
    quality_strategy: Optional[QualityStrategy] = None
    generation_strategy: Optional[GenerationStrategy] = None
    # Preservation Profile Selections
    clone_mode: Optional[str] = None
    preserve_visual_style: Optional[bool] = None
    preserve_characters: Optional[bool] = None
    preserve_environment: Optional[bool] = None
    preserve_camera_pacing: Optional[bool] = None
    preserve_trend_structure: Optional[bool] = None
    scenes: List[SceneBlueprint] = Field(default_factory=list)

    # Unified LipSync Policy
    use_lip_sync: Optional[bool] = None
    allow_lip_sync_fallback: Optional[bool] = None
    
    # Cost & Estimates (Informational only)
    estimated_video_seconds: float = 0.0
    estimated_dialogue_characters: int = 0
    estimated_generation_attempts: int = 0
    estimated_reference_assets: int = 0
    estimated_cost_usd: float = 0.0
    estimate_generated_at: Optional[datetime.datetime] = None
    
    # Approval
    status: Literal["DRAFT", "READY_FOR_APPROVAL", "APPROVED", "SUPERSEDED", "INVALID", "IN_PRODUCTION", "COMPLETED", "FAILED"] = "DRAFT"
    
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

