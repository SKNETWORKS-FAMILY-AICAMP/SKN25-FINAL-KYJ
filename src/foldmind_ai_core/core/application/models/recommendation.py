from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.core.domain.models.document_sources import SourceDocument
from foldmind_ai_core.shared.types import JsonObject, JsonValue


@dataclass(frozen=True, slots=True)
class FolderRecommendationSourceRequest:
    tenant: str
    request_text: str
    requested_at: str
    context_document_id: str | None = None
    context_folder_id: str | None = None
    task_document: JsonValue = None
    options: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FolderRecommendationSource:
    document: SourceDocument
    folder_ids: tuple[str, ...] = ()
