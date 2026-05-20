from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.domain.models.generation.results import (
    FolderRecommendationResult,
    RelatedRecommendationResult,
)
from foldmind_ai_core.core.domain.models.workflow.actions import HostActionPolicy
from foldmind_ai_core.core.domain.models.workflow.tasks import TaskSnapshot
from foldmind_ai_core.shared.types import JsonObject


@dataclass(frozen=True, slots=True)
class HostActionBuildContext:
    task: TaskSnapshot
    round_index: int
    folder_recommendation: FolderRecommendationResult | None
    related_recommendation: RelatedRecommendationResult | None
    options: JsonObject
    policy: HostActionPolicy
    document_body: str | None
    create_folder_action_id: str | None
    create_document_action_id: str | None
