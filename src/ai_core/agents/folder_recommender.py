from __future__ import annotations

from dataclasses import dataclass

from ai_core.application.use_cases.recommend_folder import RecommendFolderUseCase
from ai_core.domain.documents import SourceDocument
from ai_core.domain.tasks import FolderRecommendationResult


@dataclass(slots=True)
class FolderRecommenderAgent:
    recommender: RecommendFolderUseCase

    def recommend(self, document: SourceDocument) -> FolderRecommendationResult:
        return self.recommender.execute(document)
