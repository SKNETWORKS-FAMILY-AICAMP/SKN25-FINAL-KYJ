from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from foldmind_ai_core.shared.types import Metadata


@dataclass(frozen=True, slots=True)
class DocumentSourceIdentity:
    tenant: str
    document_id: str
    source_version: str


@dataclass(frozen=True, slots=True)
class DocumentSourceState:
    tenant: str
    document_type: str | None
    document_id: str
    source_version: str
    title: str
    created_at: str
    updated_at: str
    content_digest: str
    content_size_bytes: int
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SourceDocument:
    tenant: str
    document_type: str | None
    document_id: str
    source_version: str
    title: str
    body: str
    created_at: str
    updated_at: str
    metadata: Metadata = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        if self.title.strip():
            return f"{self.title}\n\n{self.body}".strip()
        return self.body.strip()

    @property
    def content_digest(self) -> str:
        return hashlib.sha256(self.full_text.encode("utf-8")).hexdigest()

    @property
    def content_size_bytes(self) -> int:
        return len(self.full_text.encode("utf-8"))
