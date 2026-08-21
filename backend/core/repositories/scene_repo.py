from core.models.scene import Scene
from core.repositories.base_repo import BaseProjectRepository

class SceneRepository(BaseProjectRepository[Scene]):
    def __init__(self):
        super().__init__(Scene, "scenes")
