from typing import Optional
from datetime import datetime, timezone
from core.models.character import Character
from core.repositories.base_repo import BaseProjectRepository
from core.firestore_client import get_db

class CharacterRepository(BaseProjectRepository[Character]):
    def __init__(self):
        super().__init__(Character, "characters")
        
    def get(self, user_id: str, project_id: str, doc_id: str) -> Optional[Character]:
        # 1. Try to get the new Character from the project
        char = super().get(user_id, project_id, doc_id)
        if char:
            return char
            
        # 2. Try to get legacy character_ref
        legacy_char = self._get_legacy_character(doc_id, project_id)
        if legacy_char:
            return legacy_char
            
        return None

    def _get_legacy_character(self, character_set_id: str, project_id: str) -> Optional[Character]:
        """Adapter for legacy character_refs."""
        doc = self.db.collection("character_refs").document(character_set_id).get()
        if not doc.exists:
            return None
            
        data = doc.to_dict()
        
        # Adapt legacy data into the new Character format
        # Legacy fields: art_style, character_design, veo_prefix, niche, canonical_reference_uri
        name = character_set_id  # Best guess since old system didn't have names
        
        adapted = Character(
            character_id=character_set_id,
            project_id=project_id,
            name=name,
            legacy_art_style=data.get("art_style"),
            legacy_character_design=data.get("character_design"),
            legacy_veo_prefix=data.get("veo_prefix"),
            canonical_reference_uri=data.get("canonical_reference_uri"),
            created_at=data.get("created_at") or datetime.now(timezone.utc)
        )
        return adapted
