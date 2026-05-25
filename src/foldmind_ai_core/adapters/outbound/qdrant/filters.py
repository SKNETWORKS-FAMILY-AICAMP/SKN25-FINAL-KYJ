from __future__ import annotations

from typing import Any

from foldmind_ai_core.adapters.outbound.qdrant.client import QdrantCollectionClient
from foldmind_ai_core.core.application.models.search import SearchScope
from foldmind_ai_core.shared.validation import InvalidInputError


def document_scope_filter(
    collection: QdrantCollectionClient,
    *,
    tenant: str,
    scope: SearchScope | None,
) -> Any:
    scope = scope or SearchScope()
    _validate_document_vector_scope(scope)
    document_id = scope.document_id
    document_ids = scope.document_ids
    if document_id is not None and document_ids:
        document_ids = tuple(dict.fromkeys((document_id, *document_ids)))
        document_id = None
    return collection.filter(
        tenant=tenant,
        document_type=scope.document_type,
        document_id=document_id,
        document_ids=document_ids,
        created_at=scope.created_at,
        updated_at=scope.updated_at,
        metadata_filter=scope.metadata_filter,
    )


def folder_scope_filter(
    collection: QdrantCollectionClient,
    *,
    tenant: str,
    scope: SearchScope | None,
) -> Any:
    scope = scope or SearchScope()
    _validate_folder_vector_scope(scope)
    return collection.filter(
        tenant=tenant,
        folder_ids=scope.folder_ids,
        created_at=scope.created_at,
        updated_at=scope.updated_at,
    )


def signal_scope_filter(
    collection: QdrantCollectionClient,
    *,
    tenant: str,
    signal_type: str | None,
    scope: SearchScope | None,
) -> Any:
    scope = scope or SearchScope()
    _validate_signal_vector_scope(scope)
    document_id = scope.document_id
    document_ids = scope.document_ids
    folder_ids = scope.folder_ids
    owner_kind = None
    if document_id is not None and document_ids:
        document_ids = tuple(
            dict.fromkeys((document_id, *document_ids))
        )
        document_id = None
    if document_id is not None or document_ids:
        owner_kind = "document"
    elif folder_ids:
        owner_kind = "folder"
    return collection.filter(
        tenant=tenant,
        owner_kind=owner_kind,
        document_type=scope.document_type,
        signal_type=signal_type,
        document_id=document_id,
        document_ids=document_ids,
        folder_ids=folder_ids,
        metadata_filter=scope.metadata_filter,
    )


def _validate_document_vector_scope(scope: SearchScope) -> None:
    if scope.folder_ids:
        raise InvalidInputError(
            "Document vector search scope does not support folder_ids."
        )


def _validate_folder_vector_scope(scope: SearchScope) -> None:
    if (
        scope.document_type
        or scope.document_id
        or scope.document_ids
        or scope.metadata_filter
    ):
        raise InvalidInputError(
            "Folder vector search scope only supports folder_ids and timestamp filters."
        )


def _validate_signal_vector_scope(scope: SearchScope) -> None:
    has_document_scope = scope.document_id is not None or bool(scope.document_ids)
    has_folder_scope = bool(scope.folder_ids)
    if scope.created_at or scope.updated_at:
        raise InvalidInputError(
            "Signal vector search scope supports document ids, folder ids, "
            "document_type, and metadata filters only."
        )
    if has_document_scope and has_folder_scope:
        raise InvalidInputError(
            "Signal vector search scope cannot combine document ids and folder ids."
        )
    if has_folder_scope and scope.document_type is not None:
        raise InvalidInputError(
            "Folder signal vector search scope does not support document_type."
        )
