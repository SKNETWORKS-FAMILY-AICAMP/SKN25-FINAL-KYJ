from __future__ import annotations

from typing import Any

from foldmind_ai_core.adapters.outbound.qdrant.client import QdrantCollectionClient
from foldmind_ai_core.domain.retrieval.queries import SearchScope


def document_identity_filter(
    collection: QdrantCollectionClient,
    *,
    document_id: str,
) -> Any:
    return collection.filter(
        document_id=document_id,
    )


def document_scope_filter(
    collection: QdrantCollectionClient,
    *,
    tenant: str,
    scope: SearchScope | None,
) -> Any:
    if scope is None:
        return collection.filter(tenant=tenant)
    return collection.filter(
        tenant=tenant,
        document_type=scope.document_type,
        document_id=scope.document_id,
        document_ids=scope.document_ids,
        metadata_filter=scope.metadata_filter,
    )


def folder_identity_filter(
    collection: QdrantCollectionClient,
    *,
    folder_id: str,
) -> Any:
    return collection.filter(folder_id=folder_id)


def folder_scope_filter(
    collection: QdrantCollectionClient,
    *,
    tenant: str,
    scope: SearchScope | None,
) -> Any:
    return collection.filter(
        tenant=tenant,
        folder_ids=scope.folder_ids if scope is not None else (),
    )
