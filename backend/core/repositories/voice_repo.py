from core.models.voice import Voice
from core.repositories.base_repo import BaseProjectRepository

class VoiceRepository(BaseProjectRepository[Voice]):
    def __init__(self):
        super().__init__(Voice, "voices")
