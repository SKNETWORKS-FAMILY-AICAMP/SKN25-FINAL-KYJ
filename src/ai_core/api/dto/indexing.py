from __future__ import annotations

from dataclasses import dataclass, field

from ai_core.common.types import Metadata
from ai_core.domain.documents import SourceDocument


@dataclass(slots=True)
class IndexDocumentRequest:
    document: SourceDocument


@dataclass(slots=True)
class IndexDocumentResponse:
    indexed_chunk_count: int


@dataclass(slots=True)
class DeleteDocumentIndexRequest:
    tenant: str
    entity_type: str
    entity_id: str
    metadata: Metadata = field(default_factory=dict)
