from __future__ import annotations

from dataclasses import dataclass

from ai_core.agents.folder_recommender import FolderRecommenderAgent
from ai_core.application.models.results import FolderRecommendationResult
from ai_core.domain.documents import SourceDocument


@dataclass(slots=True)
class RecommendFolderUseCase:
    folder_recommender: FolderRecommenderAgent

    def execute(self, document: SourceDocument) -> FolderRecommendationResult:
        return self.folder_recommender.recommend(document)
