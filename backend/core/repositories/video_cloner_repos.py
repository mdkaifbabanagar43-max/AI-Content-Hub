from core.models.video_cloner import SourceVideoRecord, FinalVideoRecord
from core.repositories.base_repo import BaseProjectRepository
from core.models.source_analysis import SourceAnalysis

class SourceVideoRepository(BaseProjectRepository[SourceVideoRecord]):
    def __init__(self):
        super().__init__(SourceVideoRecord, "source_videos")

class SourceAnalysisRepository(BaseProjectRepository[SourceAnalysis]):
    def __init__(self):
        super().__init__(SourceAnalysis, "source_analyses")

class FinalVideoRepository(BaseProjectRepository[FinalVideoRecord]):
    def __init__(self):
        super().__init__(FinalVideoRecord, "final_videos")
