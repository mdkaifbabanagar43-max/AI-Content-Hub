"""
Visual Identity Pack Data Models
================================
Defines persistent project-level visual identity system, multi-angle character
reference sheets, environment references, prop references, visual treatments,
and shot-level reference packs.
"""
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
import datetime

class CharacterVisualIdentity(BaseModel):
    """Canonical visual identity for a single recurring character."""
    character_id: str
    project_id: str
    name: str
    version: int = 1
    
    # Master reference sheet (multi-angle composite)
    master_sheet_uri: Optional[str] = None
    
    # Extracted panel references for shot-aware conditioning
    front_ref_uri: Optional[str] = None
    three_quarter_left_uri: Optional[str] = None
    three_quarter_right_uri: Optional[str] = None
    side_ref_uri: Optional[str] = None
    back_ref_uri: Optional[str] = None
    closeup_ref_uri: Optional[str] = None
    full_body_ref_uri: Optional[str] = None
    wardrobe_ref_uri: Optional[str] = None
    
    # Descriptors & constraints
    visual_descriptor: str = ""
    wardrobe_descriptor: str = ""
    material_notes: Optional[str] = None
    color_palette: List[str] = Field(default_factory=list)
    
    # Status & lock
    status: Literal["DRAFT", "APPROVED", "LOCKED"] = "APPROVED"
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

class EnvironmentVisualIdentity(BaseModel):
    """Canonical visual identity for a recurring environment/location."""
    environment_id: str
    project_id: str
    name: str
    version: int = 1
    
    canonical_uri: str
    wide_ref_uri: Optional[str] = None
    medium_ref_uri: Optional[str] = None
    alternate_angle_uri: Optional[str] = None
    
    lighting_descriptor: str = ""
    architectural_style: Optional[str] = None
    status: Literal["DRAFT", "APPROVED", "LOCKED"] = "APPROVED"
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

class PropVisualIdentity(BaseModel):
    """Canonical visual identity for a recurring hero prop."""
    prop_id: str
    project_id: str
    name: str
    version: int = 1
    
    canonical_uri: str
    visual_descriptor: str = ""
    material: Optional[str] = None
    status: Literal["DRAFT", "APPROVED", "LOCKED"] = "APPROVED"
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

class VisualTreatment(BaseModel):
    """Project-level aesthetic and render constraints."""
    art_style: str = "3D Pixar-style digital animation"
    color_palette: List[str] = Field(default_factory=list)
    lighting: str = "Cinematic subsurface lighting, vibrant colors"
    render_language: str = "3D digital render, volumetric illumination"
    texture_rules: str = "Clean metallic and fabric textures"
    camera_language: str = "Dynamic cinematic angles"
    negative_tokens: List[str] = Field(default_factory=list)
    source_constraints: List[str] = Field(default_factory=list)

class VisualIdentityPack(BaseModel):
    """The master visual identity package for a project."""
    pack_id: str
    project_id: str
    version: int = 1
    
    characters: Dict[str, CharacterVisualIdentity] = Field(default_factory=dict)
    environments: Dict[str, EnvironmentVisualIdentity] = Field(default_factory=dict)
    props: Dict[str, PropVisualIdentity] = Field(default_factory=dict)
    visual_treatment: VisualTreatment = Field(default_factory=VisualTreatment)
    
    status: Literal["DRAFT", "APPROVED", "LOCKED"] = "APPROVED"
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

class ShotReferencePack(BaseModel):
    """Per-shot conditioning package selected by ReferenceManager."""
    shot_id: str
    scene_id: str
    primary_character_id: Optional[str] = None
    character_refs: List[str] = Field(default_factory=list)
    environment_ref: Optional[str] = None
    prop_refs: List[str] = Field(default_factory=list)
    
    # Frames-first anchors
    start_frame_uri: Optional[str] = None
    end_frame_uri: Optional[str] = None
    mid_frame_uri: Optional[str] = None
    
    # Camera & action
    camera: str = "MEDIUM"
    action: str = ""
    motion_instruction: str = ""
    continuity_state: Dict[str, Any] = Field(default_factory=dict)
