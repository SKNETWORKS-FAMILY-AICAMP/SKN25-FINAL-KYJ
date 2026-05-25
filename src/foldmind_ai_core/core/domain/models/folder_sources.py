from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.shared.types import Metadata


@dataclass(frozen=True, slots=True)
class FolderSourceIdentity:
    tenant: str
    folder_id: str
    source_version: str


@dataclass(frozen=True, slots=True)
class SourceFolder:
    tenant: str
    folder_id: str
    source_version: str
    name: str
    created_at: str
    updated_at: str
    path: str | None = None
    parent_folder_id: str | None = None
    description: str = ""
    metadata: Metadata = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        parts = [self.name.strip()]
        if self.description.strip():
            parts.append(self.description.strip())
        if self.path and self.path.strip():
            parts.append(self.path.strip())
        return "\n\n".join(part for part in parts if part).strip()
