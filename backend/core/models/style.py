from typing import Optional, Dict, Any
from pydantic import BaseModel

class Style(BaseModel):
    style_id: str
    project_id: str
    visual_style: Optional[str] = None
    rendering_style: Optional[str] = None
    lighting: Optional[str] = None
    color_palette: Optional[str] = None
    camera_language: Optional[str] = None
    lens_language: Optional[str] = None
    depth_of_field: Optional[str] = None
    contrast: Optional[str] = None
    film_grain: Optional[str] = None
    skin_rendering: Optional[str] = None
    environment_detail: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
