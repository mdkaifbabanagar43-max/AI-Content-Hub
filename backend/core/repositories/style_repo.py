from core.models.style import Style
from core.repositories.base_repo import BaseProjectRepository

class StyleRepository(BaseProjectRepository[Style]):
    def __init__(self):
        super().__init__(Style, "styles")
