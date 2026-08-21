from typing import TypeVar, Generic, Type, Optional, List
from google.cloud import firestore
from pydantic import BaseModel
from core.firestore_client import get_db

T = TypeVar('T', bound=BaseModel)

class BaseProjectRepository(Generic[T]):
    def __init__(self, model_class: Type[T], collection_name: str):
        self.model_class = model_class
        self.collection_name = collection_name
        self.db = get_db()
        
    def _get_collection(self, user_id: str, project_id: str):
        return self.db.collection("users").document(user_id).collection("projects").document(project_id).collection(self.collection_name)
        
    def get(self, user_id: str, project_id: str, doc_id: str) -> Optional[T]:
        doc = self._get_collection(user_id, project_id).document(doc_id).get()
        if doc.exists:
            return self.model_class(**doc.to_dict())
        return None
        
    def list(self, user_id: str, project_id: str) -> List[T]:
        docs = self._get_collection(user_id, project_id).stream()
        return [self.model_class(**doc.to_dict()) for doc in docs]
        
    def save(self, user_id: str, project_id: str, doc_id: str, model_obj: T) -> bool:
        try:
            data = model_obj.model_dump(exclude_none=True)
            self._get_collection(user_id, project_id).document(doc_id).set(data, merge=True)
            return True
        except Exception as e:
            print(f"[{self.__class__.__name__}] Failed to save {doc_id}: {e}")
            return False
            
    def delete(self, user_id: str, project_id: str, doc_id: str) -> bool:
        try:
            self._get_collection(user_id, project_id).document(doc_id).delete()
            return True
        except Exception as e:
            print(f"[{self.__class__.__name__}] Failed to delete {doc_id}: {e}")
            return False
