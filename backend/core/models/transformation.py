from typing import List, Optional
from pydantic import BaseModel, Field

class ProductionTransformationRequest(BaseModel):
    # What to change
    topic: Optional[str] = Field(None, description="The new topic or subject matter (e.g., 'Make it about Bitcoin')")
    story_change: Optional[str] = Field(None, description="Explicit changes to the story events or twists")
    target_duration_seconds: Optional[float] = Field(None, description="New target duration in seconds")
    language: Optional[str] = Field(None, description="Target language (e.g., 'Hindi', 'English')")
    tone: Optional[str] = Field(None, description="The desired tone (e.g., 'funny', 'dramatic')")
    
    # Concrete Project Bibles to inject
    requested_style_id: Optional[str] = Field(None, description="Specific Style Bible ID to apply")
    requested_character_ids: List[str] = Field(default_factory=list, description="Specific Character Bible IDs to feature")
    requested_voice_id: Optional[str] = Field(None, description="Specific Voice Bible ID to use for main narrator/dialogue")
    requested_location_ids: List[str] = Field(default_factory=list, description="Specific Location Bible IDs to use")
    requested_prop_ids: List[str] = Field(default_factory=list, description="Specific Prop Bible IDs to use")
    
    # What to preserve from CloneBlueprint
    preserve_structure: bool = Field(True, description="Keep the same NarrativeBeat layout (Hook, Escalation, etc.)")
    preserve_pacing: bool = Field(True, description="Try to match the same shot/scene rhythms")
    preserve_camera_language: bool = Field(True, description="Keep the same camera angles, motions, and shot types")
    preserve_emotional_arc: bool = Field(True, description="Keep the same emotional progression per scene")
    
    additional_instructions: Optional[str] = Field(None, description="Any other specific instructions for the Director")
