from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.shared.types import Metadata


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
