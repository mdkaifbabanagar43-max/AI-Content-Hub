"""
Visual Identity Repository
==========================
Firestore persistence repository for VisualIdentityPack under:
users/{user_id}/projects/{project_id}/visual_identity_packs/{pack_id}
"""
from typing import Optional, List
from core.firestore_client import get_db
from core.models.visual_identity import VisualIdentityPack

class VisualIdentityRepository:
    def __init__(self):
        self.db = get_db()

    def _get_collection(self, user_id: str, project_id: str):
        return (
            self.db.collection("users")
            .document(user_id)
            .collection("projects")
            .document(project_id)
            .collection("visual_identity_packs")
        )

    def save(self, user_id: str, project_id: str, pack_id: str, pack: VisualIdentityPack):
        doc_ref = self._get_collection(user_id, project_id).document(pack_id)
        doc_ref.set(pack.model_dump())

    def get(self, user_id: str, project_id: str, pack_id: str) -> Optional[VisualIdentityPack]:
        doc_ref = self._get_collection(user_id, project_id).document(pack_id)
        doc = doc_ref.get()
        if doc.exists:
            return VisualIdentityPack(**doc.to_dict())
        return None

    def get_latest(self, user_id: str, project_id: str) -> Optional[VisualIdentityPack]:
        docs = self._get_collection(user_id, project_id).order_by("version", direction="DESCENDING").limit(1).get()
        for doc in docs:
            return VisualIdentityPack(**doc.to_dict())
        return None

    def list(self, user_id: str, project_id: str) -> List[VisualIdentityPack]:
        docs = self._get_collection(user_id, project_id).get()
        return [VisualIdentityPack(**doc.to_dict()) for doc in docs]
