from __future__ import annotations

from foldmind_ai_core.adapters.inbound.http.dtos.documents import (
    RetrievedDocumentDTO,
    SourceDocumentDTO,
    SourceFolderDTO,
)
from foldmind_ai_core.adapters.inbound.http.mappers.transport_values import (
    transport_value,
)
from foldmind_ai_core.core.application.models.indexing import (
    IndexDocumentCommand,
)
from foldmind_ai_core.core.application.models.retrieval import RetrievedDocument
from foldmind_ai_core.core.domain.models.document_sources import SourceDocument
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder
from foldmind_ai_core.shared.source_versions import require_source_version
from foldmind_ai_core.shared.validation import (
    InvalidInputError,
    require_aware_iso_timestamp,
    require_non_blank,
    require_optional_non_blank,
    require_optional_uuid,
    require_uuid,
    require_uuid_items,
)


def index_document_command_from_dto(dto: SourceDocumentDTO) -> IndexDocumentCommand:
    tenant = require_non_blank(dto.tenant, "tenant")
    document_id = require_uuid(dto.document_id, "document_id")
    source_version = require_source_version(dto.source_version, "source_version")
    return IndexDocumentCommand(
        document=SourceDocument(
            tenant=tenant,
            document_type=require_optional_non_blank(
                dto.document_type,
                "document_type",
            ),
            document_id=document_id,
            source_version=source_version,
            title=dto.title,
            body=dto.body,
            created_at=require_aware_iso_timestamp(dto.created_at, "created_at"),
            updated_at=require_aware_iso_timestamp(dto.updated_at, "updated_at"),
            metadata=dict(dto.metadata),
        ),
        folder_ids=_folder_ids_from_document_snapshot(
            dto,
            source_version=source_version,
        ),
    )


def source_folder_from_dto(dto: SourceFolderDTO) -> SourceFolder:
    return SourceFolder(
        tenant=require_non_blank(dto.tenant, "tenant"),
        folder_id=require_uuid(dto.folder_id, "folder_id"),
        source_version=require_source_version(dto.source_version, "source_version"),
        name=require_non_blank(dto.name, "name"),
        created_at=require_aware_iso_timestamp(dto.created_at, "created_at"),
        updated_at=require_aware_iso_timestamp(dto.updated_at, "updated_at"),
        path=dto.path,
        parent_folder_id=require_optional_uuid(
            dto.parent_folder_id,
            "parent_folder_id",
        ),
        description=dto.description,
        metadata=dict(dto.metadata),
    )


def _folder_ids_from_document_snapshot(
    dto: SourceDocumentDTO,
    *,
    source_version: str,
) -> tuple[str, ...] | None:
    snapshot = dto.folder_relation_snapshot
    if snapshot is None:
        return None
    if snapshot.source_version is not None:
        snapshot_source_version = require_source_version(
            snapshot.source_version,
            "folder_relation_snapshot.source_version",
        )
        if snapshot_source_version != source_version:
            raise InvalidInputError(
                "folder_relation_snapshot.source_version must match document.source_version."
            )
    return _unique_uuid_items(
        snapshot.folder_ids,
        "folder_relation_snapshot.folder_ids",
    )


def _unique_uuid_items(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in require_uuid_items(values, field_name):
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return tuple(unique)


def retrieved_document_dto_from_result(
    document: RetrievedDocument,
) -> RetrievedDocumentDTO:
    return RetrievedDocumentDTO(
        tenant=document.tenant,
        document_type=document.document_type,
        document_id=document.document_id,
        source_version=document.source_version,
        created_at=document.created_at,
        updated_at=document.updated_at,
        snippet=document.snippet,
        metadata=transport_value(document.metadata),
    )
