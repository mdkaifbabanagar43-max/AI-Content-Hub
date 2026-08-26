from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

class CharacterAppearance(BaseModel):
    face_shape: Optional[str] = None
    skin_tone: Optional[str] = None
    eyes: Optional[str] = None
    hair: Optional[str] = None
    facial_features: Optional[str] = None

class CharacterBody(BaseModel):
    height: Optional[str] = None
    build: Optional[str] = None
    proportions: Optional[str] = None

class CharacterClothing(BaseModel):
    top: Optional[str] = None
    inner_clothing: Optional[str] = None
    pants: Optional[str] = None
    shoes: Optional[str] = None

class CharacterAccessories(BaseModel):
    watch: Optional[str] = None
    glasses: Optional[str] = None
    backpack: Optional[str] = None
    jewelry: Optional[str] = None
    other: Optional[List[str]] = Field(default_factory=list)

class Character(BaseModel):
    character_id: str
    project_id: str
    name: str
    age: Optional[str] = None
    gender: Optional[str] = None
    
    appearance: Optional[CharacterAppearance] = None
    body: Optional[CharacterBody] = None
    clothing: Optional[CharacterClothing] = None
    accessories: Optional[CharacterAccessories] = None
    personality: Optional[List[str]] = Field(default_factory=list)
    
    canonical_reference_uri: Optional[str] = None
    legacy_reference_uri: Optional[str] = None
    
    # Legacy fallbacks for compatibility with old character_refs
    legacy_art_style: Optional[str] = None
    legacy_character_design: Optional[str] = None
    legacy_veo_prefix: Optional[str] = None
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
