from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.errors import NoCandidatesError
from foldmind_ai_core.application.services.use_case_contracts import FolderFinder
from foldmind_ai_core.domain.generation.results import (
    FolderRecommendation,
    FolderRecommendationResult,
)
from foldmind_ai_core.domain.reference.documents import SourceDocument


@dataclass(slots=True)
class RecommendFolderUseCase:
    find_folders: FolderFinder

    def execute(self, document: SourceDocument) -> FolderRecommendationResult:
        matches = self.find_folders.execute(document)
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
