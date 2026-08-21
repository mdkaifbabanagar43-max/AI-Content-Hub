from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class Voice(BaseModel):
    voice_id: str
    character_id: str
    provider: str = "elevenlabs"
    provider_voice_id: str
    language: Optional[str] = None
    accent: Optional[str] = None
    delivery_style: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
