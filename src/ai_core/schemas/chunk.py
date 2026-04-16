from __future__ import annotations

from dataclasses import dataclass, field

from ai_core.common.types import Metadata


@dataclass(slots=True)
class DocumentChunk:
    tenant: str
    entity_type: str
    entity_id: str
    version: str
    chunk_id: str
    text: str
    chunk_index: int
    start_offset: int
    end_offset: int
    folder_ids: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    metadata: Metadata = field(default_factory=dict)

    @property
    def document_key(self) -> str:
        return f"{self.tenant}:{self.entity_type}:{self.entity_id}"

    @property
    def source_key(self) -> str:
        return f"{self.document_key}:{self.version}"
