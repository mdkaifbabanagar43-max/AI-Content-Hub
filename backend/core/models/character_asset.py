from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class CharacterAsset(BaseModel):
    asset_id: str
    character_id: str
    asset_type: str  # e.g., front_portrait, three_quarter, side_profile, full_body, outfit_reference, expression_reference, character_sheet
    storage_uri: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
