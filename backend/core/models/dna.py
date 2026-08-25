"""
Source DNA Models — Canonical Clone Schema v3.0.0 (§2)
=======================================================
Nine decoupled DNA representations extracted from source media.

STRICT NARRATIVE SEPARATION (schema §3): instances of these models must NEVER
contain source plot summaries, dialogue transcripts, verbal punchlines, or
scene action prose. They carry structure, timing, and style descriptors ONLY.
Adapters in core/services/source_dna_adapter.py enforce this by construction;
tests/test_source_dna_adapter.py enforces it by scanning serialized output.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VisualStyleDNA(BaseModel):
    art_style: str
    render_language: str
    lighting_style: str
    color_palette: str
    realism_level: str
    texture_detail: Optional[str] = None


class CharacterDNA(BaseModel):
    source_character_count: int
    # Per-role visual descriptors (role, appearance summary). Never dialogue.
    characters: List[Dict[str, Any]] = Field(default_factory=list)


class EnvironmentDNA(BaseModel):
    setting_type: str  # URBAN, INTERIOR, STUDIO, FANTASY, NATURE, GENERIC
    architectural_style: Optional[str] = None
    environmental_mood: str


class CameraDNA(BaseModel):
    dominant_shot_types: List[str] = Field(default_factory=list)   # WIDE, MEDIUM, CLOSE_UP...
    motion_styles: List[str] = Field(default_factory=list)         # STATIC, DOLLY, TRACKING, PAN...
    lens_character: Optional[str] = None


class PacingDNA(BaseModel):
    average_shot_duration: float
    fastest_shot_duration: float
    slowest_shot_duration: float
    cut_frequency: str          # FAST, MODERATE, SLOW
    rhythm_description: str
    overall_intensity: str


class EditingDNA(BaseModel):
    transition_styles: List[str] = Field(default_factory=list)     # HARD_CUT, DISSOLVE, WHIP_PAN...
    framing_consistency: str    # CONSISTENT, VARIED
    visual_density: str         # LOW, MEDIUM, HIGH


class AudioDNA(BaseModel):
    has_speech: bool
    has_bgm: bool
    music_mood: Optional[str] = None
    sfx_density: str            # LOW, MEDIUM, HIGH


class NarrativeStructureDNA(BaseModel):
    """Pure structural timeline shape — NO plot text or actions."""
    hook_duration_seconds: float
    hook_intensity: str                     # HIGH, MEDIUM, LOW
    total_beats: int
    beat_types: List[str] = Field(default_factory=list)  # HOOK, SETUP, ..., RESOLUTION
    climax_position_percent: float


class TrendDNA(BaseModel):
    viral_hook_type: str
    content_format: str         # SKIT, EXPLAINER, REACTION, SHOWCASE
    pacing_archetype: str       # RAPID, STANDARD, DELIBERATE


class SourceDNACluster(BaseModel):
    """
    Bundle passed to TransformationContext.compile_prompt(). Every member is
    Optional so partial sources (e.g. Trend Cloner analyses) yield valid,
    minimal clusters instead of fabricated data.
    """
    visual_style: Optional[VisualStyleDNA] = None
    character_dna: Optional[CharacterDNA] = None
    environment_dna: Optional[EnvironmentDNA] = None
    camera_dna: Optional[CameraDNA] = None
    pacing_dna: Optional[PacingDNA] = None
    editing_dna: Optional[EditingDNA] = None
    audio_dna: Optional[AudioDNA] = None
    narrative_structure_dna: Optional[NarrativeStructureDNA] = None
    trend_dna: Optional[TrendDNA] = None