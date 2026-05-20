from __future__ import annotations

from foldmind_ai_core.adapters.inbound.http.dtos.documents import (
    RetrievedDocumentDTO,
    SourceDocumentDTO,
    SourceFolderDTO,
)
from foldmind_ai_core.adapters.inbound.http.mappers.transport_values import (
    transport_value,
)
from foldmind_ai_core.core.application.commands.indexing import (
    IndexDocumentCommand,
    IndexFolderCommand,
)
from foldmind_ai_core.core.application.commands.recommendation import RecommendFolderCommand
from foldmind_ai_core.core.application.results.workflow import RetrievedDocumentResult
from foldmind_ai_core.shared.validation import (
    require_non_blank,
    require_optional_non_blank,
    require_optional_uuid,
    require_aware_iso_timestamp,
    require_uuid,
)


def index_document_command_from_dto(dto: SourceDocumentDTO) -> IndexDocumentCommand:
    tenant = require_non_blank(dto.tenant, "tenant")
    document_id = require_uuid(dto.document_id, "document_id")
    return IndexDocumentCommand(
        tenant=tenant,
        document_type=require_optional_non_blank(dto.document_type, "document_type"),
        document_id=document_id,
        source_version=require_non_blank(dto.source_version, "source_version"),
        title=dto.title,
        body=dto.body,
        created_at=require_aware_iso_timestamp(dto.created_at, "created_at"),
        updated_at=require_aware_iso_timestamp(dto.updated_at, "updated_at"),
        metadata=dict(dto.metadata),
    )


def recommend_folder_command_from_document_dto(
    dto: SourceDocumentDTO,
) -> RecommendFolderCommand:
    return RecommendFolderCommand(
        tenant=require_non_blank(dto.tenant, "tenant"),
        document_type=require_optional_non_blank(dto.document_type, "document_type"),
        document_id=require_uuid(dto.document_id, "document_id"),
        source_version=require_non_blank(dto.source_version, "source_version"),
        title=dto.title,
        body=dto.body,
        created_at=require_aware_iso_timestamp(dto.created_at, "created_at"),
        updated_at=require_aware_iso_timestamp(dto.updated_at, "updated_at"),
        metadata=dict(dto.metadata),
    )


def index_folder_command_from_dto(dto: SourceFolderDTO) -> IndexFolderCommand:
    return IndexFolderCommand(
        tenant=require_non_blank(dto.tenant, "tenant"),
        folder_id=require_uuid(dto.folder_id, "folder_id"),
        source_version=require_non_blank(dto.source_version, "source_version"),
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


def retrieved_document_dto_from_result(
    document: RetrievedDocumentResult,
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
