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
