from __future__ import annotations

from typing import Any

from pydantic import Field

from foldmind_ai_core.adapters.inbound.http.dtos.dto_model import APIDTO


class SourceDocumentDTO(APIDTO):
    tenant: str
    document_type: str | None = None
    document_id: str
    source_version: str
    title: str
    body: str
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievedDocumentDTO(APIDTO):
    tenant: str
    document_type: str | None
    document_id: str
    source_version: str
    created_at: str = ""
    updated_at: str = ""
    snippet: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceFolderDTO(APIDTO):
    tenant: str
    folder_id: str
    source_version: str
    name: str
    created_at: str
    updated_at: str
    path: str | None = None
    parent_folder_id: str | None = None
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievedFolderDTO(APIDTO):
    tenant: str
    folder_id: str
    source_version: str
    created_at: str = ""
    updated_at: str = ""
    name: str = ""
    path: str | None = None
    description: str = ""
