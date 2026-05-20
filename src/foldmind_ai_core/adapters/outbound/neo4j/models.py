from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Neo4jDocumentNodeRecord:
    tenant: str
    document_id: str
    document_type: str | None
    source_version: str
    content_digest: str
    created_at: str
    updated_at: str
    label: str | None = None
    metadata_json: str = "{}"


@dataclass(frozen=True, slots=True)
class Neo4jFolderNodeRecord:
    tenant: str
    folder_id: str
    label: str | None = None
    source_version: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    path_snapshot: str | None = None
    parent_folder_id: str | None = None
    metadata_json: str = "{}"


@dataclass(frozen=True, slots=True)
class Neo4jRelationshipRecord:
    tenant: str
    confidence: float
    metadata_json: str = "{}"


@dataclass(frozen=True, slots=True)
class Neo4jDocumentSignalNodeRecord:
    signal_id: str
    tenant: str
    signal_type: str
    signal_key: str
    text: str
    document_id: str
    source_version: str
    content_digest: str
    attributes_json: str = "{}"
    confidence: float | None = None
    metadata_json: str = "{}"


@dataclass(frozen=True, slots=True)
class Neo4jFolderSignalNodeRecord:
    signal_id: str
    tenant: str
    folder_id: str
    source_version: str
    signal_type: str
    signal_key: str
    text: str
    related_document_id: str | None = None
    attributes_json: str = "{}"
    confidence: float | None = None
    metadata_json: str = "{}"
