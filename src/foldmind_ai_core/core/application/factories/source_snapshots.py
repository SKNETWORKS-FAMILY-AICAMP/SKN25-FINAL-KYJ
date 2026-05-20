from __future__ import annotations

from foldmind_ai_core.core.application.commands.indexing import (
    IndexDocumentCommand,
    IndexFolderCommand,
)
from foldmind_ai_core.core.application.commands.recommendation import (
    RecommendFolderCommand,
)
from foldmind_ai_core.core.domain.models.reference.documents import SourceDocument
from foldmind_ai_core.core.domain.models.reference.folders import SourceFolder


def source_document_from_index_command(command: IndexDocumentCommand) -> SourceDocument:
    return SourceDocument(
        tenant=command.tenant,
        document_type=command.document_type,
        document_id=command.document_id,
        source_version=command.source_version,
        title=command.title,
        body=command.body,
        created_at=command.created_at,
        updated_at=command.updated_at,
        metadata=dict(command.metadata),
    )


def source_document_from_recommend_folder_command(
    command: RecommendFolderCommand,
) -> SourceDocument:
    return SourceDocument(
        tenant=command.tenant,
        document_type=command.document_type,
        document_id=command.document_id,
        source_version=command.source_version,
        title=command.title,
        body=command.body,
        created_at=command.created_at,
        updated_at=command.updated_at,
        metadata=dict(command.metadata),
    )


def source_folder_from_index_command(command: IndexFolderCommand) -> SourceFolder:
    return SourceFolder(
        tenant=command.tenant,
        folder_id=command.folder_id,
        source_version=command.source_version,
        name=command.name,
        created_at=command.created_at,
        updated_at=command.updated_at,
        path=command.path,
        parent_folder_id=command.parent_folder_id,
        description=command.description,
        metadata=dict(command.metadata),
    )
