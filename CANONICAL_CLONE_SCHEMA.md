# CANONICAL CLONE SCHEMA — CLONEFRAME UNIVERSAL ENGINE

**Specification Version:** 3.0.0  
**Domain:** Universal Ingestion, DNA Extraction, Preservation, & Transformation  

---

## 1. Universal Conceptual Object: `CloneIntent`

The single canonical request contract passed from frontend to the transformation boundary:

```python
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class CharacterMode(str, Enum):
    PRESERVE_SOURCE = "PRESERVE_SOURCE" # Reuse original characters & visual descriptors
    CREATE_NEW = "CREATE_NEW"           # Invent brand new characters in matching art style
    MIXED = "MIXED"                     # Keep selected source characters, generate new ones for remainder

class EnvironmentMode(str, Enum):
    PRESERVE_SOURCE = "PRESERVE_SOURCE" # Reuse source background / world settings
    CREATE_NEW = "CREATE_NEW"           # Generate brand new environments matching new story
    ADAPT = "ADAPT"                     # Keep visual world aesthetic but adapt scene locations

class StoryMode(str, Enum):
    NEW_STORY = "NEW_STORY"                     # Completely new narrative driven by user creative intent
    STRUCTURE_INSPIRED = "STRUCTURE_INSPIRED"   # Follows beat timings/escalation without copying plot
    TREND_INSPIRED = "TREND_INSPIRED"           # Uses viral trend rhythm & hook formula

class PreservationProfile(BaseModel):
    """User-controlled toggles defining exactly which DNA categories to clone."""
    preserve_visual_style: bool = Field(True, description="Clone art style, render language, lighting, color palette")
    preserve_characters: bool = Field(False, description="Clone source character appearance & identities")
    preserve_environment: bool = Field(False, description="Clone source world/background settings")
    preserve_camera_language: bool = Field(True, description="Clone camera motion, angles, lens styles")
    preserve_pacing_editing: bool = Field(True, description="Clone shot durations, cut frequency, intensity")
    preserve_audio_style: bool = Field(False, description="Clone sound design density & music mood")
    preserve_voice_style: bool = Field(False, description="Clone narrator tempo & delivery cadence")
    preserve_trend_structure: bool = Field(False, description="Clone viral hook formula & escalation curve")

class CreativeIntent(BaseModel):
    """User's explicit description of what NEW content to create."""
    topic: str = Field(..., description="Primary topic or subject (e.g. 'Bank Heist in Paris')")
    story_change: Optional[str] = Field(None, description="Specific plot events, gags, or narrative twists")
    niche: Optional[str] = Field("General", description="Target niche / genre")
    genre: Optional[str] = Field("Comedy", description="Story genre")
    tone: Optional[str] = Field("Humorous", description="Emotional tone")
    audience: Optional[str] = Field("General", description="Target demographic")
    language: Optional[str] = Field("English", description="Dialogue/narration language")
    target_duration_seconds: Optional[float] = Field(None, description="Requested video duration")
    aspect_ratio: str = Field("9:16", description="Video format aspect ratio")

class CloneIntent(BaseModel):
    """The master universal input for any video creation or cloning operation."""
    user_id: str
    project_id: str
    source_video_id: Optional[str] = None
    source_url: Optional[str] = None
    
    # Preservation & Policy Configuration
    preservation_profile: PreservationProfile = Field(default_factory=PreservationProfile)
    character_mode: CharacterMode = Field(CharacterMode.CREATE_NEW)
    environment_mode: EnvironmentMode = Field(EnvironmentMode.CREATE_NEW)
    story_mode: StoryMode = Field(StoryMode.NEW_STORY)
    
    # Explicit User Creative Intent
    creative_intent: CreativeIntent
    
    # Specific Entity Bibles (Optional user overrides)
    requested_character_ids: List[str] = Field(default_factory=list)
    requested_style_id: Optional[str] = None
    requested_location_ids: List[str] = Field(default_factory=list)
    requested_voice_id: Optional[str] = None
    requested_prop_ids: List[str] = Field(default_factory=list)
```

---

## 2. Independent Source DNA Representations

Extracted by the `SourceAnalyzer` into 9 decoupled DNA models:

```python
class VisualStyleDNA(BaseModel):
    art_style: str
    render_language: str
    lighting_style: str
    color_palette: str
    realism_level: str
    texture_detail: Optional[str] = None

class CharacterDNA(BaseModel):
    source_character_count: int
    characters: List[Dict[str, Any]] # Visual description, clothing, physical traits

class EnvironmentDNA(BaseModel):
    setting_type: str # Urban, Interior, Studio, Fantasy, Nature
    architectural_style: Optional[str] = None
    environmental_mood: str

class CameraDNA(BaseModel):
    dominant_shot_types: List[str] # WIDE, MEDIUM, CLOSE_UP
    motion_styles: List[str]      # STATIC, DOLLY, TRACKING, PAN
    lens_character: Optional[str] = None

class PacingDNA(BaseModel):
    average_shot_duration: float
    fastest_shot_duration: float
    slowest_shot_duration: float
    cut_frequency: str # FAST, MODERATE, SLOW
    rhythm_description: str
    overall_intensity: str

class EditingDNA(BaseModel):
    transition_styles: List[str] # HARD_CUT, DISSOLVE, WHIP_PAN
    framing_consistency: str
    visual_density: str

class AudioDNA(BaseModel):
    has_speech: bool
    has_bgm: bool
    music_mood: Optional[str] = None
    sfx_density: str # LOW, MEDIUM, HIGH

class NarrativeStructureDNA(BaseModel):
    """Pure structural timeline shape (NO dialogue text or plot actions)."""
    hook_duration_seconds: float
    hook_intensity: str
    total_beats: int
    beat_types: List[str] # HOOK, ESCALATION, TWIST, RESOLUTION
    climax_position_percent: float

class TrendDNA(BaseModel):
    viral_hook_type: str
    content_format: str # SKIT, EXPLAINER, REACTION, SHOWCASE
    pacing_archetype: str
```

---

## 3. Strict Narrative Separation Guarantee

```
+-------------------------------------------------------------------------------+
|                      STRICT NARRATIVE SEPARATION PRINCIPLE                    |
+------------------------------------+------------------------------------------+
| PASSED TO LLM (When Enabled)       | - VisualStyleDNA (art style, lighting)   |
|                                    | - CameraDNA (cinematography language)    |
|                                    | - PacingDNA (scene cut durations)        |
|                                    | - NarrativeStructureDNA (beat timings)   |
|                                    | - User CreativeIntent (NEW story topic)  |
+------------------------------------+------------------------------------------+
| STRIPPED / FORBIDDEN BY DEFAULT    | - Original plot summaries & gags         |
|                                    | - Original dialogue scripts & transcripts|
|                                    | - Original scene visual actions          |
|                                    | - Original verbal punchlines             |
+------------------------------------+------------------------------------------+
```
