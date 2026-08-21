from core.repositories.base_repo import BaseProjectRepository
from core.models.state import SceneState

class SceneStateRepository(BaseProjectRepository[SceneState]):
    def __init__(self):
        super().__init__(SceneState, "scene_states")
