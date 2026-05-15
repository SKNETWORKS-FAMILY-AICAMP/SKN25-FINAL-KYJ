from __future__ import annotations

import json
from typing import Any

from foldmind_ai_core.domain.knowledge_graph.models import (
    DocumentConceptProjection,
    DocumentRelationshipProjection,
    FolderRelationshipProjection,
    TagProjection,
)
from foldmind_ai_core.domain.profiling.models import ProfileConcept


def replace_document_relationships(
    session: Any,
    projection: DocumentRelationshipProjection,
) -> None:
    _merge_document_relationship_identity(session, projection)
    _delete_document_relationship_edges(session, projection)
    for folder_id in projection.folder_ids:
        _link_document_to_folder(session, projection, folder_id)
    for tag_id in projection.tag_ids:
        _link_document_to_tag(session, projection, tag_id)


def replace_document_projection(
    session: Any,
    *,
    relationships: DocumentRelationshipProjection,
    concepts: DocumentConceptProjection,
) -> None:
    replace_document_relationships(session, relationships)
    replace_document_concepts(session, concepts)


def replace_document_concepts(session: Any, projection: DocumentConceptProjection) -> None:
    _merge_document_concept_identity(session, projection)
    _delete_document_concept_edges(session, projection)
    for concept in projection.concepts:
        _merge_concept(session, projection.tenant, concept)
        _link_document_to_concept(session, projection, concept)


def replace_folder_hierarchy(session: Any, projection: FolderRelationshipProjection) -> None:
    _merge_projected_folder(session, projection)
    _delete_folder_parent_edges(session, projection)
    if projection.parent_folder_id is None:
        return
    _link_folder_to_parent(session, projection)


def upsert_tag(session: Any, projection: TagProjection) -> None:
    _merge_tag(
        session,
        projection.tenant,
        projection.tag_id,
        projection.label,
        projection.normalized_label,
        metadata=projection.metadata,
    )


def delete_document_projection(
    session: Any,
    *,
    document_id: str,
) -> None:
    session.run(
        """
        MATCH (d:Document {document_id: $document_id})
        DETACH DELETE d
        """,
        document_id=document_id,
    )


def delete_folder_projection(session: Any, *, folder_id: str) -> None:
    session.run(
        """
        MERGE (f:Folder {folder_id: $folder_id})
        SET f.deleted = true
        WITH f
        OPTIONAL MATCH (f)-[outgoing_child_of:CHILD_OF]->()
        DELETE outgoing_child_of
        WITH f
        OPTIONAL MATCH (f)<-[incoming_child_of:CHILD_OF]-()
        DELETE incoming_child_of
        WITH f
        OPTIONAL MATCH (:Document)-[in_folder:IN_FOLDER]->(f)
        DELETE in_folder
        """,
        folder_id=folder_id,
    )


def _delete_document_relationship_edges(
    session: Any,
    projection: DocumentRelationshipProjection,
) -> None:
    session.run(
        """
        MATCH (d:Document {document_id: $document_id})-[r:IN_FOLDER|HAS_TAG]->()
        DELETE r
        """,
        document_id=projection.document_id,
    )


def _delete_document_concept_edges(
    session: Any,
    projection: DocumentConceptProjection,
) -> None:
    session.run(
        """
        MATCH (d:Document {document_id: $document_id})-[r:ABOUT]->()
        DELETE r
        """,
        document_id=projection.document_id,
    )


def _delete_folder_parent_edges(
    session: Any,
    projection: FolderRelationshipProjection,
) -> None:
    session.run(
        """
        MATCH (f:Folder {tenant: $tenant, folder_id: $folder_id})-[r:CHILD_OF]->()
        DELETE r
        """,
        tenant=projection.tenant,
        folder_id=projection.folder_id,
    )


def _merge_document_relationship_identity(
    session: Any,
    projection: DocumentRelationshipProjection,
) -> None:
    session.run(
        """
        MERGE (d:Document {document_id: $document_id})
        SET d.tenant = $tenant,
            d.document_type = $document_type,
            d.source_version = $source_version
        """,
        tenant=projection.tenant,
        document_id=projection.document_id,
        document_type=projection.document_type,
        source_version=projection.source_version,
    )


def _merge_document_concept_identity(
    session: Any,
    projection: DocumentConceptProjection,
) -> None:
    session.run(
        """
        MERGE (d:Document {document_id: $document_id})
        SET d.tenant = $tenant,
            d.document_type = $document_type,
            d.label = $label,
            d.source_version = $source_version,
            d.metadata_json = $metadata_json
        """,
        tenant=projection.tenant,
        document_id=projection.document_id,
        document_type=projection.document_type,
        label=projection.title,
        source_version=projection.source_version,
        metadata_json=json.dumps(projection.metadata, ensure_ascii=False),
    )


def _link_document_to_folder(
    session: Any,
    projection: DocumentRelationshipProjection,
    folder_id: str,
) -> None:
    _merge_folder_placeholder(
        session,
        projection.tenant,
        folder_id,
    )
    session.run(
        """
        MATCH (d:Document {document_id: $document_id})
        MATCH (f:Folder {folder_id: $folder_id})
        WHERE coalesce(f.deleted, false) = false
        MERGE (d)-[r:IN_FOLDER]->(f)
        SET r.tenant = $tenant,
            r.confidence = 1.0,
            r.metadata_json = '{}'
        """,
        tenant=projection.tenant,
        document_id=projection.document_id,
        folder_id=folder_id,
    )


def _link_document_to_tag(
    session: Any,
    projection: DocumentRelationshipProjection,
    tag_id: str,
) -> None:
    _merge_tag(session, projection.tenant, tag_id, tag_id, _normalize_label(tag_id))
    session.run(
        """
        MATCH (d:Document {document_id: $document_id})
        MATCH (t:Tag {tag_id: $tag_id})
        MERGE (d)-[r:HAS_TAG]->(t)
        SET r.tenant = $tenant,
            r.confidence = 1.0,
            r.metadata_json = '{}'
        """,
        tenant=projection.tenant,
        document_id=projection.document_id,
        tag_id=tag_id,
    )


def _merge_concept(session: Any, tenant: str, concept: ProfileConcept) -> None:
    session.run(
        """
        MERGE (c:Concept {concept_id: $concept_id})
        SET c.tenant = $tenant,
            c.label = $label,
            c.concept_key = $concept_key,
            c.concept_version = '1',
            c.metadata_json = $metadata_json
        """,
        tenant=tenant,
        concept_id=concept.concept_id,
        concept_key=concept.concept_key,
        label=concept.label,
        metadata_json=json.dumps(concept.metadata, ensure_ascii=False),
    )


def _link_document_to_concept(
    session: Any,
    projection: DocumentConceptProjection,
    concept: ProfileConcept,
) -> None:
    session.run(
        """
        MATCH (d:Document {document_id: $document_id})
        MATCH (c:Concept {concept_id: $concept_id})
        MERGE (d)-[r:ABOUT]->(c)
        SET r.tenant = $tenant,
            r.confidence = $confidence,
            r.metadata_json = $metadata_json
        """,
        tenant=projection.tenant,
        document_id=projection.document_id,
        concept_id=concept.concept_id,
        confidence=_concept_confidence(projection, concept),
        metadata_json=json.dumps(
            _concept_edge_metadata(projection, concept),
            ensure_ascii=False,
        ),
    )


def _concept_confidence(
    projection: DocumentConceptProjection,
    concept: ProfileConcept,
) -> float:
    if concept.confidence is not None:
        return concept.confidence
    if projection.profile_confidence is not None:
        return projection.profile_confidence
    return 1.0


def _concept_edge_metadata(
    projection: DocumentConceptProjection,
    concept: ProfileConcept,
) -> dict[str, Any]:
    return {
        "source_version": projection.source_version,
        "profile_version": projection.profile_version,
        "profile_confidence": projection.profile_confidence,
        "evidence_chunk_ids": list(concept.evidence_chunk_ids),
        **projection.metadata,
    }


def _merge_projected_folder(
    session: Any,
    projection: FolderRelationshipProjection,
) -> None:
    _merge_folder(
        session,
        projection.tenant,
        projection.folder_id,
        projection.folder_id,
        parent_folder_id=projection.parent_folder_id,
        source_version=projection.source_version,
    )


def _link_folder_to_parent(session: Any, projection: FolderRelationshipProjection) -> None:
    parent_folder_id = projection.parent_folder_id
    if parent_folder_id is None:
        return
    _merge_folder_placeholder(
        session,
        projection.tenant,
        parent_folder_id,
    )
    session.run(
        """
        MATCH (child:Folder {folder_id: $folder_id})
        MATCH (parent:Folder {folder_id: $parent_folder_id})
        WHERE coalesce(parent.deleted, false) = false
        MERGE (child)-[r:CHILD_OF]->(parent)
        SET r.tenant = $tenant,
            r.confidence = 1.0,
            r.metadata_json = '{}'
        """,
        tenant=projection.tenant,
        folder_id=projection.folder_id,
        parent_folder_id=parent_folder_id,
    )


def _merge_folder(
    session: Any,
    tenant: str,
    folder_id: str,
    label: str,
    *,
    source_version: str | None,
    path_snapshot: str | None = None,
    parent_folder_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    session.run(
        """
        MERGE (f:Folder {folder_id: $folder_id})
        SET f.tenant = $tenant,
            f.label = $label,
            f.path_snapshot = $path_snapshot,
            f.parent_folder_id = $parent_folder_id,
            f.metadata_json = $metadata_json,
            f.deleted = false
        FOREACH (_ IN CASE WHEN $source_version IS NULL THEN [] ELSE [1] END |
            SET f.source_version = $source_version
        )
        """,
        tenant=tenant,
        folder_id=folder_id,
        label=label,
        path_snapshot=path_snapshot,
        parent_folder_id=parent_folder_id,
        source_version=source_version,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
    )


def _merge_folder_placeholder(session: Any, tenant: str, folder_id: str) -> None:
    session.run(
        """
        MERGE (f:Folder {folder_id: $folder_id})
        ON CREATE SET f.tenant = $tenant,
                      f.deleted = false
        SET f.tenant = coalesce(f.tenant, $tenant),
            f.deleted = coalesce(f.deleted, false)
        """,
        tenant=tenant,
        folder_id=folder_id,
    )


def _merge_tag(
    session: Any,
    tenant: str,
    tag_id: str,
    label: str,
    normalized_label: str,
    *,
    metadata: dict[str, Any] | None = None,
) -> None:
    session.run(
        """
        MERGE (t:Tag {tag_id: $tag_id})
        SET t.tenant = $tenant,
            t.label = $label,
            t.normalized_label = $normalized_label,
            t.metadata_json = $metadata_json
        """,
        tenant=tenant,
        tag_id=tag_id,
        label=label,
        normalized_label=normalized_label,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
    )


def _normalize_label(value: str) -> str:
    return "_".join(value.casefold().split())
