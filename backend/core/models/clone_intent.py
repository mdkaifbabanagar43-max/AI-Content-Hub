"""
CloneIntent Models — Canonical Clone Schema v3.0.0 (§1)
========================================================
The universal conceptual object passed from any caller (Video Cloner, Trend
Cloner, Idea Studio) to the UniversalCreativeDirector transformation boundary.

P3 verdicts baked in (plan §3/§10):
- D3/Q1 : CharacterMode.MIXED is accepted and STORED, but degraded to
          PRESERVE_SOURCE ∩ requested_character_ids by the normalizer until
          a per-character selection UI ships.
- Q3    : Legacy top-level booleans on ProductionTransformationRequest remain
          permanently dual-accepted — never hard-deleted.
- Q5    : Narrative-originality threshold exposed as config.ORIGINALITY_THRESHOLD.
"""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class CharacterMode(str, Enum):
    PRESERVE_SOURCE = "PRESERVE_SOURCE"  # Reuse original characters & visual descriptors
    CREATE_NEW = "CREATE_NEW"            # Invent brand-new characters in matching art style
    MIXED = "MIXED"                      # Degraded per D3: treated as PRESERVE_SOURCE ∩ requested ids


class EnvironmentMode(str, Enum):
    PRESERVE_SOURCE = "PRESERVE_SOURCE"  # Reuse source background / world settings
    CREATE_NEW = "CREATE_NEW"            # Generate brand-new environments for the new story
    ADAPT = "ADAPT"                      # Keep world aesthetic, adapt scene locations


class StoryMode(str, Enum):
    NEW_STORY = "NEW_STORY"                    # Completely new narrative from user intent
    STRUCTURE_INSPIRED = "STRUCTURE_INSPIRED"  # Beat timings/escalation without copying plot
    TREND_INSPIRED = "TREND_INSPIRED"          # Viral trend rhythm & hook formula


class PreservationProfile(BaseModel):
    """User-controlled toggles defining exactly which DNA categories to clone."""
    preserve_visual_style: bool = Field(True, description="Clone art style, render language, lighting, color palette")
    preserve_characters: bool = Field(False, description="Clone source character appearance & identities")
    preserve_environment: bool = Field(False, description="Clone source world/background settings")
    preserve_camera_language: bool = Field(True, description="Clone camera motion, angles, lens styles")
    preserve_pacing_editing: bool = Field(True, description="Clone shot durations, cut frequency, intensity")
    preserve_audio_style: bool = Field(False, description="Clone sound design density & music mood (forward-compat)")
    preserve_voice_style: bool = Field(False, description="Clone narrator tempo & delivery cadence (forward-compat)")
    preserve_trend_structure: bool = Field(False, description="Clone viral hook formula & escalation curve")


class CreativeIntent(BaseModel):
    """User's explicit description of what NEW content to create."""
    topic: str = Field(..., description="Primary topic or subject")
    story_change: Optional[str] = Field(None, description="Specific plot events, gags, or twists")
    niche: Optional[str] = Field("General", description="Target niche / genre")
    genre: Optional[str] = Field("Comedy", description="Story genre")
    tone: Optional[str] = Field("Humorous", description="Emotional tone")
    audience: Optional[str] = Field("General", description="Target demographic")
    language: Optional[str] = Field("English", description="Dialogue/narration language")
    target_duration_seconds: Optional[float] = Field(None, description="Requested video duration")
    aspect_ratio: str = Field("9:16", description="Video format aspect ratio")


class CloneIntent(BaseModel):
    """Master universal input for any video creation or cloning operation."""
    user_id: str
    project_id: str
    source_video_id: Optional[str] = None
    source_url: Optional[str] = None

    preservation_profile: PreservationProfile = Field(default_factory=PreservationProfile)
    character_mode: CharacterMode = Field(CharacterMode.CREATE_NEW)
    environment_mode: EnvironmentMode = Field(EnvironmentMode.CREATE_NEW)
    story_mode: StoryMode = Field(StoryMode.NEW_STORY)

    creative_intent: CreativeIntent

    requested_character_ids: List[str] = Field(default_factory=list)
    requested_style_id: Optional[str] = None
    requested_location_ids: List[str] = Field(default_factory=list)
    requested_voice_id: Optional[str] = None
    requested_prop_ids: List[str] = Field(default_factory=list)


def build_preservation_profile(
    *,
    preserve_visual_style: bool = True,
    preserve_characters: bool = False,
    preserve_environment: bool = False,
    preserve_camera_pacing: bool = True,
    preserve_trend_structure: bool = False,
    preserve_structure: bool | None = None,
    preserve_pacing: bool | None = None,
    preserve_camera_language: bool | None = None,
    preserve_emotional_arc: bool | None = None,
    preserve_audio_style: bool | None = None,
    preserve_voice_style: bool | None = None,
) -> PreservationProfile:
    """
    Pure §5a mapper: synthesizes the eight-toggle PreservationProfile from any
    combination of legacy flags. Deterministic, no I/O; exercised by the
    parity table in tests/test_clone_intent_mapping.py.

    Key mappings (plan §5a):
      - preserve_camera_pacing splits into camera_language AND pacing_editing
      - granular preserve_pacing / preserve_camera_language OR into that pair
      - preserve_structure=True folds into STRUCTURE_INSPIRED semantics upstream
        (story_mode is resolved by the Phase-B normalizer, not here)
      - preserve_emotional_arc has no independent consumer today — accepted for
        Q3 dual-accept compatibility and folded into pacing directive text.
    """
    camera_language = preserve_camera_pacing
    pacing_editing = preserve_camera_pacing

    if preserve_camera_language is True:
        camera_language = True
    if preserve_pacing is True:
        pacing_editing = True

    return PreservationProfile(
        preserve_visual_style=preserve_visual_style,
        preserve_characters=preserve_characters,
        preserve_environment=preserve_environment,
        preserve_camera_language=camera_language,
        preserve_pacing_editing=pacing_editing,
        preserve_audio_style=bool(preserve_audio_style),
        preserve_voice_style=bool(preserve_voice_style),
        preserve_trend_structure=preserve_trend_structure,
    )