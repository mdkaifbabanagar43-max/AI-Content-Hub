import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
import uuid

class SourceMediaMetadata(BaseModel):
    duration_seconds: float = Field(description="Exact duration of the media in seconds")
    width: int = Field(description="Width of the video in pixels")
    height: int = Field(description="Height of the video in pixels")
    fps: float = Field(description="Frames per second")
    aspect_ratio: str = Field(description="Calculated aspect ratio (e.g. 16:9, 9:16)")
    has_audio: bool = Field(description="Whether the file contains an audio track")
    audio_duration_seconds: Optional[float] = Field(None, description="Exact duration of audio track if available")
    video_codec: Optional[str] = Field(None, description="Video codec used")
    audio_codec: Optional[str] = Field(None, description="Audio codec used")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")

class SourceSceneSegment(BaseModel):
    scene_number: int = Field(description="Sequential scene index starting at 1")
    start_seconds: float = Field(description="Exact start timestamp of the scene")
    end_seconds: float = Field(description="Exact end timestamp of the scene")
    duration_seconds: float = Field(description="Exact duration of the scene")
    detection_method: Literal["SEMANTIC", "VISUAL", "MANUAL", "HYBRID"] = Field(
        default="VISUAL", description="How the cut was detected"
    )

class SceneSemanticAnalysis(BaseModel):
    scene_number: int = Field(description="The scene index this applies to")
    narrative_purpose: str = Field(description="Purpose in the narrative arc")
    visual_action: str = Field(description="What is visually happening in the shot")
    emotion: Literal["curious", "surprised", "confused", "excited", "fearful", "angry", "sad", "neutral", "unknown"] = Field(
        default="neutral", description="Dominant emotion"
    )
    pacing_intensity: Literal["LOW", "MEDIUM", "HIGH", "CLIMACTIC"] = Field(
        default="MEDIUM", description="Pacing and intensity of the action"
    )
    shot_type: Literal["ESTABLISHING", "WIDE", "MEDIUM", "CLOSE_UP", "EXTREME_CLOSE_UP", "OVER_SHOULDER", "POV", "UNKNOWN"] = Field(
        default="UNKNOWN", description="Cinematographic shot type"
    )
    camera_motion: Literal["STATIC", "TRACKING", "PAN", "TILT", "DOLLY", "ZOOM", "UNKNOWN"] = Field(
        default="UNKNOWN", description="Primary camera movement"
    )
    character_roles: List[Literal["PROTAGONIST", "SECONDARY_CHARACTER", "NARRATOR", "BACKGROUND_PERSON", "UNKNOWN"]] = Field(
        default_factory=list, description="Roles of characters present in the shot"
    )
    location_summary: Optional[str] = Field(None, description="Summary of the location setting")
    prop_summary: Optional[str] = Field(None, description="Summary of key props visible")
    lighting_summary: Optional[str] = Field(None, description="Summary of lighting conditions")
    transition: Optional[str] = Field(None, description="Transition from the previous scene")
    dialogue_intent: Optional[str] = Field(None, description="Semantic intent of any dialogue")

class HookAnalysis(BaseModel):
    hook_type: Literal["VISUAL_SHOCK", "DIRECT_QUESTION", "MYSTERY", "CONFLICT", "ROLE_REVERSAL", "PROMISE", "OTHER", "NONE"] = Field(
        description="Type of hook used"
    )
    hook_start_seconds: Optional[float] = Field(None, description="Start timestamp of the hook")
    hook_end_seconds: Optional[float] = Field(None, description="End timestamp of the hook")
    hook_description: Optional[str] = Field(None, description="Description of how the hook works")
    confidence: float = Field(description="Confidence level in the hook analysis (0.0 to 1.0)")

class CTAAnalysis(BaseModel):
    exists: bool = Field(description="True if a call to action is present")
    start_seconds: Optional[float] = Field(None, description="Start timestamp of CTA")
    end_seconds: Optional[float] = Field(None, description="End timestamp of CTA")
    type: Literal["FOLLOW", "LIKE", "COMMENT", "SUBSCRIBE", "DOWNLOAD", "VISIT_LINK", "NONE", "OTHER"] = Field(
        default="NONE", description="Type of CTA"
    )
    description: Optional[str] = Field(None, description="Detailed description of the CTA")

class SourceAudioProfile(BaseModel):
    has_speech: bool = Field(default=False)
    speech_tempo: Literal["SLOW", "MODERATE", "FAST", "RAPID", "UNKNOWN"] = Field(default="UNKNOWN")
    has_background_music: bool = Field(default=False)
    music_mood: Optional[str] = Field(None)
    sfx_present: bool = Field(default=False)

class SourceDialogueBeat(BaseModel):
    start_seconds: Optional[float] = Field(None)
    end_seconds: Optional[float] = Field(None)
    text: str = Field(description="The actual dialogue spoken")
    speaker_role: Literal["PROTAGONIST", "SECONDARY_CHARACTER", "NARRATOR", "BACKGROUND_PERSON", "UNKNOWN"] = Field(
        default="UNKNOWN", description="Who is speaking"
    )
    emotion: str = Field(default="neutral")
    delivery_style: str = Field(default="conversational")

class SourceVisualStyle(BaseModel):
    art_style: str = Field(description="Exact rendering style")
    character_design: str = Field(description="Detailed physical aesthetic")
    visual_style_summary: Optional[str] = Field(None)
    color_tone: Optional[str] = Field(None)
    lighting_summary: Optional[str] = Field(None)
    animation_or_live_action: Optional[Literal["ANIMATION", "LIVE_ACTION", "UNKNOWN"]] = Field(None)
    realism_level: Optional[str] = Field(None)
    content_elements: Optional[str] = Field(None, description="Incidental source content elements e.g. meme inserts or live action references")

class SourceAnalysis(BaseModel):
    analysis_id: str = Field(default_factory=lambda: f"ana_{uuid.uuid4().hex[:8]}")
    source_video_id: str
    media_metadata: SourceMediaMetadata
    transcript_text: str = Field(description="Complete raw spoken transcript")
    scenes: List[SourceSceneSegment] = Field(default_factory=list)
    semantic_scenes: List[SceneSemanticAnalysis] = Field(default_factory=list)
    hook: HookAnalysis
    cta: CTAAnalysis
    visual_style: SourceVisualStyle
    audio_profile: SourceAudioProfile
    dialogue_beats: List[SourceDialogueBeat] = Field(default_factory=list)
    analyzed_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    analyzer_version: str = Field(default="1.0.0")
