from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from foldmind_ai_core.shared.types import Metadata


@dataclass(frozen=True, slots=True)
class SourceFolder:
    tenant: str
    folder_id: str
    source_version: str
    name: str
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


@dataclass(frozen=True, slots=True)
class FolderVectorProjection:
    tenant: str
    folder_id: str
    source_version: str
    embedding_input: str
    embedding_input_hash: str
    embedding_model: str
    embedding_version: str
    index_schema_version: str

    @classmethod
    def from_source(
        cls,
        folder: SourceFolder,
        *,
        embedding_model: str,
        embedding_version: str,
        index_schema_version: str,
    ) -> FolderVectorProjection:
        embedding_input = _folder_embedding_input(folder)
        return cls(
            tenant=folder.tenant,
            folder_id=folder.folder_id,
            source_version=folder.source_version,
            embedding_input=embedding_input,
            embedding_input_hash=_hash_text(embedding_input),
            embedding_model=embedding_model,
            embedding_version=embedding_version,
            index_schema_version=index_schema_version,
        )


def _folder_embedding_input(folder: SourceFolder) -> str:
    parts = [
        folder.name,
        folder.path or "",
        folder.description,
    ]
    return "\n\n".join(part.strip() for part in parts if part.strip())


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
