from __future__ import annotations

from dataclasses import dataclass, field

from ai_core.common.types import Metadata


@dataclass(slots=True)
class SourceDocument:
    tenant: str
    entity_type: str
    entity_id: str
    version: str
    title: str
    body: str
    folder_ids: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    metadata: Metadata = field(default_factory=dict)

    @property
    def document_key(self) -> str:
        return f"{self.tenant}:{self.entity_type}:{self.entity_id}"

    @property
    def source_key(self) -> str:
        return f"{self.document_key}:{self.version}"

    @property
    def full_text(self) -> str:
        if self.title.strip():
            return f"{self.title}\n\n{self.body}".strip()
        return self.body.strip()


@dataclass(slots=True)
class SourceFolder:
    tenant: str
    folder_id: str
    name: str
    path: str | None = None
    parent_folder_id: str | None = None
    description: str = ""
    metadata: Metadata = field(default_factory=dict)

    @property
    def folder_key(self) -> str:
        return f"{self.tenant}:{self.folder_id}"

    @property
    def full_text(self) -> str:
        parts = [self.name.strip()]
        if self.description.strip():
            parts.append(self.description.strip())
        if self.path and self.path.strip():
            parts.append(self.path.strip())
        return "\n\n".join(part for part in parts if part).strip()
