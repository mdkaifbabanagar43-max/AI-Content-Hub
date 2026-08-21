from typing import Optional, Dict, Any
from pydantic import BaseModel

class Location(BaseModel):
    location_id: str
    project_id: str
    name: str
    architecture: Optional[str] = None
    environment: Optional[str] = None
    walls: Optional[str] = None
    floor: Optional[str] = None
    furniture: Optional[str] = None
    lighting: Optional[str] = None
    signature_elements: Optional[str] = None
    reference_uri: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
