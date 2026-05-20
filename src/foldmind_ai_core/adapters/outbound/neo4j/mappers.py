from __future__ import annotations

import json
from typing import Any

from foldmind_ai_core.adapters.outbound.neo4j.models import (
    Neo4jDocumentSignalNodeRecord,
    Neo4jDocumentNodeRecord,
    Neo4jFolderNodeRecord,
    Neo4jFolderSignalNodeRecord,
    Neo4jRelationshipRecord,
)
from foldmind_ai_core.core.application.projections.graph import (
    DocumentRelationshipProjection,
    DocumentSignalProjection,
    DocumentSignalNodeProjection,
    FolderRelationshipProjection,
    FolderSignalNodeProjection,
    FolderSignalProjection,
)
from foldmind_ai_core.core.application.queries.retrieval import SearchScope
from foldmind_ai_core.core.application.queries.scope_matching import (
    matches_timestamp_scope,
)
from foldmind_ai_core.core.domain.models.retrieval.results import RetrievedDocument


def document_from_node(node: Any) -> RetrievedDocument:
    record = document_node_from_neo4j(node)
    return RetrievedDocument(
        tenant=record.tenant,
        document_type=record.document_type,
        document_id=record.document_id,
        source_version=record.source_version,
        created_at=record.created_at,
        updated_at=record.updated_at,
        metadata=_metadata_json_dict(record.metadata_json),
    )


def document_node_from_neo4j(node: Any) -> Neo4jDocumentNodeRecord:
    return Neo4jDocumentNodeRecord(
        tenant=_required_node_text(node, "tenant"),
        document_id=_required_node_text(node, "document_id"),
        document_type=_optional_node_text(node, "document_type", default="") or None,
        source_version=_optional_node_text(node, "source_version", default=""),
        content_digest=_optional_node_text(node, "content_digest", default=""),
        created_at=_required_node_text(node, "created_at"),
        updated_at=_required_node_text(node, "updated_at"),
        label=_optional_node_text(node, "label", default="") or None,
        metadata_json=_optional_node_text(node, "metadata_json", default="{}"),
    )


def document_relationship_node_from_projection(
    projection: DocumentRelationshipProjection,
) -> Neo4jDocumentNodeRecord:
    return Neo4jDocumentNodeRecord(
        tenant=projection.tenant,
        document_id=projection.document_id,
        document_type=projection.document_type,
        source_version=projection.source_version,
        content_digest=projection.content_digest,
        created_at=projection.created_at,
        updated_at=projection.updated_at,
    )


def document_signal_node_from_projection(
    projection: DocumentSignalProjection,
) -> Neo4jDocumentNodeRecord:
    return Neo4jDocumentNodeRecord(
        tenant=projection.tenant,
        document_id=projection.document_id,
        document_type=projection.document_type,
        source_version=projection.source_version,
        content_digest=projection.content_digest,
        created_at=projection.created_at,
        updated_at=projection.updated_at,
        label=projection.title,
        metadata_json=json.dumps(projection.metadata, ensure_ascii=False),
    )


def document_signal_record_from_projection(
    signal: DocumentSignalNodeProjection,
) -> Neo4jDocumentSignalNodeRecord:
    return Neo4jDocumentSignalNodeRecord(
        signal_id=signal.signal_id,
        tenant=signal.tenant,
        signal_type=signal.signal_type,
        signal_key=signal.signal_key,
        text=signal.text,
        document_id=signal.document_id,
        source_version=signal.source_version,
        content_digest=signal.content_digest,
        index_input_digest=signal.index_input_digest,
        attributes_json=json.dumps(signal.attributes, ensure_ascii=False),
        confidence=signal.confidence,
        generation_model=signal.generation_model,
        metadata_json=json.dumps(signal.metadata, ensure_ascii=False),
    )


def folder_signal_record_from_projection(
    signal: FolderSignalNodeProjection,
) -> Neo4jFolderSignalNodeRecord:
    return Neo4jFolderSignalNodeRecord(
        signal_id=signal.signal_id,
        tenant=signal.tenant,
        folder_id=signal.folder_id,
        source_version=signal.source_version,
        index_input_digest=signal.index_input_digest,
        signal_type=signal.signal_type,
        signal_key=signal.signal_key,
        text=signal.text,
        related_document_id=signal.related_document_id,
        attributes_json=json.dumps(signal.attributes, ensure_ascii=False),
        confidence=signal.confidence,
        generation_model=signal.generation_model,
        metadata_json=json.dumps(signal.metadata, ensure_ascii=False),
    )


def folder_node_from_projection(
    projection: FolderRelationshipProjection,
) -> Neo4jFolderNodeRecord:
    return Neo4jFolderNodeRecord(
        tenant=projection.tenant,
        folder_id=projection.folder_id,
        label=projection.name,
        source_version=projection.source_version,
        created_at=projection.created_at,
        updated_at=projection.updated_at,
        path_snapshot=projection.path,
        parent_folder_id=projection.parent_folder_id,
    )


def folder_reference_node(*, tenant: str, folder_id: str) -> Neo4jFolderNodeRecord:
    return Neo4jFolderNodeRecord(tenant=tenant, folder_id=folder_id)


def signal_relationship(
    *,
    projection: DocumentSignalProjection,
    signal: DocumentSignalNodeProjection,
) -> Neo4jRelationshipRecord:
    return Neo4jRelationshipRecord(
        tenant=projection.tenant,
        confidence=signal.confidence if signal.confidence is not None else 1.0,
        metadata_json=json.dumps(
            {
                "signal_id": signal.signal_id,
                "source_version": projection.source_version,
                "content_digest": projection.content_digest,
                "index_input_digest": projection.index_input_digest,
                "signal_generation_version": projection.signal_generation_version,
                **projection.metadata,
            },
            ensure_ascii=False,
        ),
    )


def folder_signal_relationship(
    *,
    projection: FolderSignalProjection,
    signal: FolderSignalNodeProjection,
) -> Neo4jRelationshipRecord:
    return Neo4jRelationshipRecord(
        tenant=projection.tenant,
        confidence=signal.confidence if signal.confidence is not None else 1.0,
        metadata_json=json.dumps(
            {
                "signal_id": signal.signal_id,
                "source_version": projection.source_version,
                "index_input_digest": projection.index_input_digest,
            },
            ensure_ascii=False,
        ),
    )


def matches_scope(document: RetrievedDocument, scope: SearchScope | None) -> bool:
    if scope is None:
        return True
    if scope.document_type is not None and document.document_type != scope.document_type:
        return False
    if scope.document_id is not None and document.document_id != scope.document_id:
        return False
    if scope.document_ids and document.document_id not in scope.document_ids:
        return False
    if not matches_timestamp_scope(
        created_at=document.created_at,
        updated_at=document.updated_at,
        scope=scope,
    ):
        return False
    return all(
        document.metadata.get(key) == value
        for key, value in scope.metadata_filter.items()
    )


def _metadata_json_dict(value: object) -> dict[str, Any]:
    if not isinstance(value, str) or not value:
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("Neo4j metadata_json must decode to an object.")
    return parsed


def _required_node_text(node: Any, key: str) -> str:
    value = node[key]
    if not isinstance(value, str):
        raise ValueError(f"Neo4j {key} must be a string.")
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"Neo4j {key} must not be blank.")
    return stripped


def _optional_node_text(node: Any, key: str, *, default: str) -> str:
    value = node.get(key)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(f"Neo4j {key} must be a string.")
    stripped = value.strip()
    return stripped or default
