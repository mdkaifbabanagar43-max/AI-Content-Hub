from typing import Optional, List
from core.models.source_analysis import SourceAnalysis
from core.repositories.base_repo import BaseRepository
import datetime

class SourceAnalysisRepository(BaseRepository[SourceAnalysis]):
    def __init__(self):
        super().__init__(SourceAnalysis, "source_analyses")

    def save(self, user_id: str, analysis: SourceAnalysis) -> SourceAnalysis:
        # Override save to ensure we link to project
        # actually, SourceAnalysis has no user_id or project_id in its schema directly,
        # but it is saved under the user_id's path in BaseRepository.
        # It's better to store under user_id/projects/project_id/source_analyses/source_video_id
        # Wait, BaseRepository stores in users/{user_id}/{collection_name}/{doc_id}
        # To make it project-scoped, we construct the ID or override the save.
        pass
