from core.repositories.base_repo import BaseProjectRepository
from core.models.attempt import GenerationAttempt

class GenerationAttemptRepository(BaseProjectRepository[GenerationAttempt]):
    def __init__(self):
        super().__init__(GenerationAttempt, "generation_attempts")
