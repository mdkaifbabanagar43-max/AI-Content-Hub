import uuid
from typing import List, Optional
from google.cloud import firestore
from core.firestore_client import get_db
from core.models.blueprint import ProductionBlueprint

class BlueprintRepository:
    def __init__(self):
        self.db = get_db()
        
    def _doc_key(self, blueprint_id: str, version: int) -> str:
        return f"{blueprint_id}_v{version}"

    def _get_ref(self, user_id: str, project_id: str, doc_key: str):
        return self.db.collection("users").document(user_id) \
                      .collection("projects").document(project_id) \
                      .collection("blueprints").document(doc_key)
                      
    def _get_collection(self, user_id: str, project_id: str):
        return self.db.collection("users").document(user_id) \
                      .collection("projects").document(project_id) \
                      .collection("blueprints")

    def save(self, user_id: str, blueprint: ProductionBlueprint) -> str:
        """
        Saves a blueprint revision under a deterministic versioned document ID (e.g. bp_xxx_v1).
        Preserves existing revisions without overwriting.
        """
        if not blueprint.blueprint_id:
            blueprint.blueprint_id = f"bp_{uuid.uuid4().hex[:8]}"
            
        doc_key = self._doc_key(blueprint.blueprint_id, blueprint.blueprint_version)
        doc_ref = self._get_ref(user_id, blueprint.project_id, doc_key)
        data = blueprint.model_dump()
        doc_ref.set(data)
        return blueprint.blueprint_id
        
    def get(self, user_id: str, project_id: str, blueprint_id: str, version: Optional[int] = None) -> Optional[ProductionBlueprint]:
        """
        Retrieves a blueprint. If version is specified, retrieves that exact revision.
        If version is None, retrieves the latest revision for the blueprint_id.
        """
        if version is not None:
            doc_key = self._doc_key(blueprint_id, version)
            doc = self._get_ref(user_id, project_id, doc_key).get()
            if doc.exists:
                return ProductionBlueprint(**doc.to_dict())
            # Legacy fallback check (raw doc id)
            legacy_doc = self._get_ref(user_id, project_id, blueprint_id).get()
            if legacy_doc.exists:
                bp = ProductionBlueprint(**legacy_doc.to_dict())
                if bp.blueprint_version == version:
                    return bp
            return None

        # Query for latest revision of this specific blueprint_id
        try:
            docs = self._get_collection(user_id, project_id) \
                       .where("blueprint_id", "==", blueprint_id) \
                       .order_by("blueprint_version", direction=firestore.Query.DESCENDING) \
                       .limit(1).stream()
            for doc in docs:
                return ProductionBlueprint(**doc.to_dict())
        except Exception as e:
            print(f"[BlueprintRepo] Stream query failed: {e}")

        # Fallback: Check direct document if stored unversioned or stream filter
        try:
            all_docs = self._get_collection(user_id, project_id).stream()
            matched = [ProductionBlueprint(**d.to_dict()) for d in all_docs if d.to_dict().get("blueprint_id") == blueprint_id]
            if matched:
                matched.sort(key=lambda b: b.blueprint_version, reverse=True)
                return matched[0]
        except Exception as e:
            print(f"[BlueprintRepo] Fallback loop failed: {e}")

        legacy_doc = self._get_ref(user_id, project_id, blueprint_id).get()
        if legacy_doc.exists:
            return ProductionBlueprint(**legacy_doc.to_dict())
            
        return None
        
    def create_version(self, user_id: str, project_id: str, blueprint_id: str, new_blueprint: ProductionBlueprint) -> ProductionBlueprint:
        """
        Creates a new version revision for an existing blueprint identity.
        Marks any previous APPROVED version as SUPERSEDED.
        """
        latest = self.get(user_id, project_id, blueprint_id)
        new_version = (latest.blueprint_version + 1) if latest else 1
        
        if latest and latest.status == "APPROVED":
            latest.status = "SUPERSEDED"
            self.save(user_id, latest)
            
        new_blueprint.blueprint_id = blueprint_id
        new_blueprint.blueprint_version = new_version
        new_blueprint.project_id = project_id
        new_blueprint.status = "READY_FOR_APPROVAL"
        self.save(user_id, new_blueprint)
        return new_blueprint

    def list_versions(self, user_id: str, project_id: str, blueprint_id: str) -> List[ProductionBlueprint]:
        """Lists all revisions of a specific blueprint in ascending order."""
        try:
            docs = self._get_collection(user_id, project_id) \
                       .where("blueprint_id", "==", blueprint_id) \
                       .order_by("blueprint_version", direction=firestore.Query.ASCENDING).stream()
            results = [ProductionBlueprint(**doc.to_dict()) for doc in docs]
            if results:
                return results
        except Exception:
            pass
            
        all_docs = self._get_collection(user_id, project_id).stream()
        matched = [ProductionBlueprint(**d.to_dict()) for d in all_docs if d.to_dict().get("blueprint_id") == blueprint_id]
        matched.sort(key=lambda b: b.blueprint_version)
        return matched

    def get_latest(self, user_id: str, project_id: str) -> Optional[ProductionBlueprint]:
        """Gets the most recently modified blueprint across the project."""
        docs = self._get_collection(user_id, project_id) \
                   .order_by("blueprint_version", direction=firestore.Query.DESCENDING) \
                   .limit(1).stream()
                   
        for doc in docs:
            return ProductionBlueprint(**doc.to_dict())
        return None

    def list_all(self, user_id: str, project_id: str) -> List[ProductionBlueprint]:
        """Lists all blueprint documents for a project."""
        docs = self._get_collection(user_id, project_id) \
                   .order_by("blueprint_version", direction=firestore.Query.ASCENDING).stream()
        return [ProductionBlueprint(**doc.to_dict()) for doc in docs]
