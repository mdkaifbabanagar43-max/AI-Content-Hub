from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class Scene(BaseModel):
    scene_id: str
    project_id: str
    scene_number: int
    duration: float
    character_ids: List[str] = Field(default_factory=list)
    location_id: Optional[str] = None
    prop_ids: List[str] = Field(default_factory=list)
    style_id: Optional[str] = None
    
    action: Optional[str] = None
    emotion: Optional[str] = None
    dialogue: Optional[str] = None
    camera: Optional[str] = None
    lighting_override: Optional[str] = None
    continuity_notes: Optional[str] = None
    
    generation_status: str = "pending"
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
