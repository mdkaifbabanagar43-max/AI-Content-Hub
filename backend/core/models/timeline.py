from typing import List, Optional, Literal, Any, Dict
from pydantic import BaseModel, Field
import datetime

class AudioAsset(BaseModel):
    asset_id: str
    asset_type: Literal["dialogue", "sfx", "music"] = "dialogue"
    uri: str
    duration: float
    start_time: float
    end_time: float
    scene_id: Optional[str] = None
    character_id: Optional[str] = None
    voice_id: Optional[str] = None
    volume: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TimelineItem(BaseModel):
    scene_id: str
    scene_number: int
    start_time: float = 0.0
    end_time: float = 0.0
    expected_duration: float
    actual_video_duration: float = 0.0
    final_scene_duration: float = 0.0
    video_uri: Optional[str] = None
    normalized_video_uri: Optional[str] = None
    lipsynced_video_uri: Optional[str] = None
    dialogue_assets: List[AudioAsset] = Field(default_factory=list)
    sfx_assets: List[AudioAsset] = Field(default_factory=list)
    music_assets: List[AudioAsset] = Field(default_factory=list)
    transition: Literal["CUT", "FADE"] = "CUT"
    status: str = "PENDING"

class ProductionTimeline(BaseModel):
    project_id: str
    total_duration: float = 0.0
    items: List[TimelineItem] = Field(default_factory=list)
    audio_tracks: List[AudioAsset] = Field(default_factory=list) # Global tracks (like music)
    video_tracks: List[Any] = Field(default_factory=list)
    version: int = 1
    validation_status: str = "PENDING"
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

class FinalVideo(BaseModel):
    project_id: str
    timeline_id: str
    output_uri: str
    duration: float
    resolution: str
    fps: int
    audio_present: bool
    scenes_count: int
    status: str = "COMPLETED"
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
