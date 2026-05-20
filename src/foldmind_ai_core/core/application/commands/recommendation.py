from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.shared.types import Metadata


@dataclass(frozen=True, slots=True)
class RecommendFolderCommand:
    tenant: str
    document_type: str | None
    document_id: str
    source_version: str
    title: str
    body: str
    created_at: str
    updated_at: str
    folder_ids: tuple[str, ...] = ()
    metadata: Metadata = field(default_factory=dict)
