from core.models.prop import Prop
from core.repositories.base_repo import BaseProjectRepository

class PropRepository(BaseProjectRepository[Prop]):
    def __init__(self):
        super().__init__(Prop, "props")
