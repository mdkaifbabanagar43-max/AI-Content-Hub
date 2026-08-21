from typing import Optional, Dict, Any
from pydantic import BaseModel

class Prop(BaseModel):
    prop_id: str
    project_id: str
    name: str
    type: Optional[str] = None
    color: Optional[str] = None
    material: Optional[str] = None
    shape: Optional[str] = None
    defining_details: Optional[str] = None
    reference_uri: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
