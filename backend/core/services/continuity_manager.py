from typing import Optional
from datetime import datetime, timezone
from core.models.context import GenerationContext
from core.models.state import SceneState
from core.repositories.state_repo import SceneStateRepository

class ContinuityManager:
    def __init__(self):
        self.state_repo = SceneStateRepository()
        
    def get_previous_state(self, context: GenerationContext, previous_scene_id: str) -> Optional[SceneState]:
        """
        Loads the SceneState of the previous scene if it exists.
        """
        if not previous_scene_id:
            return None
        return self.state_repo.get(context.user_id, context.project_id, previous_scene_id)
        
    def save_state(self, context: GenerationContext, state: SceneState):
        """
        Saves the resulting state after a scene completes successfully.
        """
        state.updated_at = datetime.now(timezone.utc)
        if not state.created_at:
            state.created_at = state.updated_at
        self.state_repo.save(context.user_id, context.project_id, state.scene_id, state)
