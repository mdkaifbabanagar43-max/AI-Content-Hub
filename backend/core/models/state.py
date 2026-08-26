from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

class CharacterState(BaseModel):
    character_id: str
    current_location: Optional[str] = None
    emotional_state: Optional[str] = None
    orientation: Optional[str] = None
    clothing_state: Optional[str] = None
    held_objects: List[str] = Field(default_factory=list)
    visible_accessories: List[str] = Field(default_factory=list)
    action_state: Optional[str] = None

class EnvironmentState(BaseModel):
    location_id: Optional[str] = None
    time_of_day: Optional[str] = None
    weather: Optional[str] = None
    lighting_state: Optional[str] = None
    important_environment_changes: Optional[str] = None

class PropState(BaseModel):
    prop_id: str
    current_holder: Optional[str] = None
    current_location: Optional[str] = None
    visibility: Optional[str] = None
    important_state: Optional[str] = None

class StoryState(BaseModel):
    facts_discovered: List[str] = Field(default_factory=list)
    events_completed: List[str] = Field(default_factory=list)
    objects_acquired: List[str] = Field(default_factory=list)
    important_narrative_conditions: Optional[str] = None

class SceneState(BaseModel):
    scene_id: str
    project_id: str
    character_states: List[CharacterState] = Field(default_factory=list)
    environment_state: Optional[EnvironmentState] = None
    prop_states: List[PropState] = Field(default_factory=list)
    story_state: Optional[StoryState] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
