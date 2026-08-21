from typing import Optional, List
from core.repositories.base_repo import BaseProjectRepository
from core.models.clone_blueprint import CloneBlueprint

class CloneBlueprintRepository(BaseProjectRepository[CloneBlueprint]):
    def __init__(self):
        super().__init__(model_class=CloneBlueprint, collection_name="clone_blueprints")
        
    def get_version(self, user_id: str, project_id: str, clone_blueprint_id: str, version: int) -> Optional[CloneBlueprint]:
        doc_id = f"{clone_blueprint_id}_v{version}"
        return self.get(user_id, project_id, doc_id)
        
    def get_latest(self, user_id: str, project_id: str, clone_blueprint_id: str) -> Optional[CloneBlueprint]:
        # Search all versions and return the highest
        versions = self.list_versions(user_id, project_id, clone_blueprint_id)
        if not versions:
            return None
        return max(versions, key=lambda b: b.clone_blueprint_version)
        
    def list_versions(self, user_id: str, project_id: str, clone_blueprint_id: str) -> List[CloneBlueprint]:
        # Query docs starting with the ID
        all_blueprints = self.list(user_id, project_id)
        # Filter in memory (fine for limited version histories)
        return [b for b in all_blueprints if b.clone_blueprint_id == clone_blueprint_id]
        
    def save(self, user_id: str, project_id: str, doc_id: str, model_obj: CloneBlueprint) -> bool:
        # Enforce doc_id matches the versioned ID pattern
        expected_doc_id = f"{model_obj.clone_blueprint_id}_v{model_obj.clone_blueprint_version}"
        if doc_id != expected_doc_id:
            raise ValueError(f"doc_id must be {expected_doc_id}")
            
        # Enforce security boundaries
        if model_obj.user_id != user_id or model_obj.project_id != project_id:
            raise PermissionError("Blueprint ownership mismatch against path.")
            
        # Immutability Check: Do not overwrite if it exists
        doc_ref = self._get_collection(user_id, project_id).document(doc_id)
        if doc_ref.get().exists:
            raise ValueError(f"Version {model_obj.clone_blueprint_version} of CloneBlueprint {model_obj.clone_blueprint_id} already exists. Mutations must create a new version.")
            
        # Use underlying save
        return super().save(user_id, project_id, doc_id, model_obj)
