from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.commands.recommendation import RecommendFolderCommand
from foldmind_ai_core.core.application.errors import NoCandidatesError
from foldmind_ai_core.core.application.factories.source_snapshots import (
    source_document_from_recommend_folder_command,
)
from foldmind_ai_core.core.application.capabilities.retrieval import FolderSearchCapability
from foldmind_ai_core.core.application.queries.retrieval import FolderSearchQuery
from foldmind_ai_core.core.application.results.retrieval import (
    FolderRecommendationResultItem,
    RecommendFolderResult,
)


@dataclass(slots=True)
class RecommendFolderUseCase:
    find_folders: FolderSearchCapability

    def execute(self, command: RecommendFolderCommand) -> RecommendFolderResult:
        document = source_document_from_recommend_folder_command(command)
        matches = self.find_folders.execute(
            FolderSearchQuery(
                tenant=document.tenant,
                text=document.full_text,
                excluded_folder_ids=command.folder_ids,
            )
        ).results
        if not matches:
            raise NoCandidatesError("No folder candidates found.")

        recommendations = [
            FolderRecommendationResultItem(
                folder_id=match.folder.folder_id,
                reason=match.reason or "Folder is related to similar indexed documents.",
                score=match.score,
            )
            for match in matches
        ]
        return RecommendFolderResult(
            primary=recommendations[0],
            alternatives=tuple(recommendations[1:]),
        )
