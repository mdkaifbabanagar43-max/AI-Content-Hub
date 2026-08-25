from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, model_validator

class ProductionTransformationRequest(BaseModel):
    # What to change (User Creative Intent)
    topic: Optional[str] = Field(None, description="The new topic or subject matter (e.g., 'Make it about Bitcoin')")
    story_change: Optional[str] = Field(None, description="Explicit changes to the story events or twists")
    niche: Optional[str] = Field(None, description="Target niche / genre (e.g., 'Comedy', 'Crypto')")
    target_duration_seconds: Optional[float] = Field(None, description="New target duration in seconds")
    language: Optional[str] = Field(None, description="Target language (e.g., 'Hindi', 'English')")
    tone: Optional[str] = Field(None, description="The desired tone (e.g., 'funny', 'dramatic')")
    
    # Concrete Project Bibles to inject (if any)
    requested_style_id: Optional[str] = Field(None, description="Specific Style Bible ID to apply")
    requested_character_ids: List[str] = Field(default_factory=list, description="Specific Character Bible IDs to feature")
    requested_voice_id: Optional[str] = Field(None, description="Specific Voice Bible ID to use for main narrator/dialogue")
    requested_location_ids: List[str] = Field(default_factory=list, description="Specific Location Bible IDs to use")
    requested_prop_ids: List[str] = Field(default_factory=list, description="Specific Prop Bible IDs to use")
    
    # What to preserve from CloneBlueprint (User Authoritative Selections)
    preserve_visual_style: bool = Field(True, description="Preserve source art style, lighting, render language, and color palette")
    preserve_characters: bool = Field(False, description="Preserve source character designs & visual identity")
    preserve_environment: bool = Field(False, description="Preserve source background world/setting")
    preserve_camera_pacing: bool = Field(True, description="Preserve source camera motion, shot variety, and pacing rhythm")
    preserve_trend_structure: bool = Field(False, description="Preserve viral hook and structural trend timing")
    
    # Presets / Modes: 'style_only', 'characters_and_style', 'full_visual_clone', 'trend_inspired', 'custom'
    clone_mode: Optional[str] = Field("style_only", description="Preset clone mode selected by user")
    
    # Legacy / Granular compatibility flags
    preserve_structure: bool = Field(True, description="Keep the same NarrativeBeat layout (Hook, Escalation, etc.)")
    preserve_pacing: bool = Field(True, description="Try to match the same shot/scene rhythms")
    preserve_camera_language: bool = Field(True, description="Keep the same camera angles, motions, and shot types")
    preserve_emotional_arc: bool = Field(True, description="Keep the same emotional progression per scene")
    
    additional_instructions: Optional[str] = Field(None, description="Any other specific instructions for the Director")

    @model_validator(mode="before")
    @classmethod
    def map_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Map topic / prompt aliases
            if "topic" not in data or not data["topic"]:
                if "target_topic" in data and data["target_topic"]:
                    data["topic"] = data["target_topic"]
            if "language" not in data or not data["language"]:
                if "target_language" in data and data["target_language"]:
                    data["language"] = data["target_language"]
            if "niche" not in data or not data["niche"]:
                if "target_niche" in data and data["target_niche"]:
                    data["niche"] = data["target_niche"]
            if "tone" not in data or not data["tone"]:
                if "humor_level" in data and data["humor_level"]:
                    data["tone"] = f"Humor: {data['humor_level']}"
            
            # Map preservation toggles if passed in short/preset form
            if "visual_style" in data and "preserve_visual_style" not in data:
                data["preserve_visual_style"] = bool(data["visual_style"])
            if "characters" in data and "preserve_characters" not in data:
                data["preserve_characters"] = bool(data["characters"])
            if "environment" in data and "preserve_environment" not in data:
                data["preserve_environment"] = bool(data["environment"])
            if "camera_pacing" in data and "preserve_camera_pacing" not in data:
                data["preserve_camera_pacing"] = bool(data["camera_pacing"])
                
            # If explicit character IDs are requested, default preserve_characters to True
            if data.get("requested_character_ids") and len(data.get("requested_character_ids")) > 0:
                data.setdefault("preserve_characters", True)
                
            # Mode presets auto-sync
            if data.get("clone_mode") == "characters_only":
                # Contract preset "Character Clone": keep characters + art style,
                # regenerate environment/camera/pacing (P3/Q2 gap-closer)
                data.setdefault("preserve_visual_style", True)
                data.setdefault("preserve_characters", True)
                data.setdefault("preserve_environment", False)
                data.setdefault("preserve_camera_pacing", False)
            elif data.get("clone_mode") == "characters_and_style":
                data.setdefault("preserve_visual_style", True)
                data.setdefault("preserve_characters", True)
                data.setdefault("preserve_environment", False)
                data.setdefault("preserve_camera_pacing", True)
            elif data.get("clone_mode") == "full_visual_clone":
                data.setdefault("preserve_visual_style", True)
                data.setdefault("preserve_characters", True)
                data.setdefault("preserve_environment", True)
                data.setdefault("preserve_camera_pacing", True)
            elif data.get("clone_mode") == "trend_inspired":
                data.setdefault("preserve_visual_style", False)
                data.setdefault("preserve_characters", False)
                data.setdefault("preserve_environment", False)
                data.setdefault("preserve_camera_pacing", True)
                data.setdefault("preserve_trend_structure", True)
            elif data.get("clone_mode") == "style_only":
                data.setdefault("preserve_visual_style", True)
                data.setdefault("preserve_characters", False)
                data.setdefault("preserve_environment", False)
                data.setdefault("preserve_camera_pacing", True)

        return data
