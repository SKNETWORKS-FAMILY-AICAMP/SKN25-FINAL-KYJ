from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.domain.generation.results import (
    FolderRecommendationResult,
    RelatedRecommendationResult,
)
from foldmind_ai_core.domain.workflow.actions import HostActionPolicy
from foldmind_ai_core.domain.workflow.tasks import TaskSnapshot
from foldmind_ai_core.shared.types import Metadata


@dataclass(frozen=True, slots=True)
class HostActionBuildContext:
    task: TaskSnapshot
    round_index: int
    folder_recommendation: FolderRecommendationResult | None
    related_recommendation: RelatedRecommendationResult | None
    options: Metadata
    policy: HostActionPolicy
    document_body: str | None
    create_folder_action_id: str | None
    create_document_action_id: str | None
