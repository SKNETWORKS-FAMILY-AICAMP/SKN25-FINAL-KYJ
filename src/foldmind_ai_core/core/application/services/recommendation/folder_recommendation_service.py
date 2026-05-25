from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.models.recommendation import FolderRecommendationSource
from foldmind_ai_core.core.application.errors import NoCandidatesError
from foldmind_ai_core.core.application.models.generation import (
    FolderRecommendation,
    FolderRecommendationResult,
)
from foldmind_ai_core.core.application.models.retrieval import FolderSearchQuery
from foldmind_ai_core.core.application.services.retrieval.folder_search_service import (
    FolderSearchService,
)


@dataclass(slots=True)
class FolderRecommendationService:
    folder_search: FolderSearchService

    async def recommend(
        self,
        source: FolderRecommendationSource,
    ) -> FolderRecommendationResult:
        document = source.document
        matches = await self.folder_search.search(
            FolderSearchQuery(
                tenant=document.tenant,
                text=document.full_text,
                excluded_folder_ids=source.folder_ids,
            )
        )
        if not matches:
            raise NoCandidatesError("No folder candidates found.")

        recommendations = [
            FolderRecommendation(
                folder_id=match.folder.folder_id,
                reason=match.reason or "Folder is related to similar indexed documents.",
                score=match.score,
            )
            for match in matches
        ]
        return FolderRecommendationResult(
            primary=recommendations[0],
            alternatives=recommendations[1:],
        )
