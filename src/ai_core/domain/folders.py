from __future__ import annotations

from dataclasses import dataclass, field

from ai_core.common.types import Metadata


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


@dataclass(slots=True)
class IndexedFolder:
    tenant: str
    folder_id: str
    name: str
    path: str | None = None
    parent_folder_id: str | None = None
    description: str = ""
    metadata: Metadata = field(default_factory=dict)

    @classmethod
    def from_source(cls, folder: SourceFolder) -> IndexedFolder:
        return cls(
            tenant=folder.tenant,
            folder_id=folder.folder_id,
            name=folder.name,
            path=folder.path,
            parent_folder_id=folder.parent_folder_id,
            description=folder.description,
            metadata=dict(folder.metadata),
        )

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
