# Shared Pydantic Models
# All request models used across routers

from pydantic import BaseModel
from typing import Optional, List


# --- Idea Studio Models ---
class IdeaRequest(BaseModel):
    topic: str
    language: str = "English"

class BrainstormRequest(BaseModel):
    topic: str
    language: str = "English"

class PreviewRequest(BaseModel):
    title: str
    hook: str
    mood: str
    voice_name: str = "en-US-Journey-D"
    language: str = "English"

class ProductionRequest(BaseModel):
    title: str
    hook: str
    platform: str = "tiktok"
    duration: str = "30s"
    mood: str = "informative"
    voice_name: str = "en-US-Journey-D"
    language: str = "English"
    script: Optional[str] = None

class FinalRenderRequest(BaseModel):
    script: str
    audio_base64: str
    visual_plan: list
    user_id: str
    topic: str
    mood: str
    platform: str


# --- Repurposer Models ---
class AnalyzeRequest(BaseModel):
    youtube_url: str

class CutRequest(BaseModel):
    start_time: str
    end_time: str
    style: str = "Intense"
    caption_style: str = "bold_viral"
    subtitle_preset: str = "bold_viral"
    hook_boost: bool = False
    mode: str = "standard"
    gcs_path: Optional[str] = None
    resolution: int = 1080
    video_url: Optional[str] = None
    content_type: str = "podcast"
    layout_mode: str = "podcast_stack"
    min_width: int = 1080


# --- Render Models ---
class RenderRequest(BaseModel):
    audio_base64: str
    pexels_search_term: str
    script: str
    platform: str = "tiktok"
    visual_plan: List[str] = []
    user_id: str = "demo_user"
    topic: str = "Untitled Project"
    mood: str = "Viral"
    thumbnail_url: str = ""
    subtitle_preset: str = "bold_viral"
    hook_boost: bool = False


# --- Voice Models ---
class VoiceoverRequest(BaseModel):
    text: str
    voice_name: str = "en-US-Journey-D"


# --- Project Models ---
class SaveProjectRequest(BaseModel):
    user_id: str
    topic: str
    video_url: str
    script: str = ""
    start_time: str = ""
    platform: str = "tiktok"
    mood: str = "fast"
