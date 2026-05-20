from __future__ import annotations

from typing import Any

from foldmind_ai_core.adapters.outbound.neo4j.mappers import (
    document_signal_record_from_projection,
    document_relationship_node_from_projection,
    document_signal_node_from_projection,
    folder_signal_record_from_projection,
    folder_signal_relationship,
    folder_node_from_projection,
    folder_reference_node,
    signal_relationship,
)
from foldmind_ai_core.adapters.outbound.neo4j.models import (
    Neo4jDocumentSignalNodeRecord,
    Neo4jFolderNodeRecord,
    Neo4jFolderSignalNodeRecord,
)
from foldmind_ai_core.core.application.projections.graph import (
    DocumentFolderRelationProjection,
    DocumentRelationshipProjection,
    DocumentSignalProjection,
    DocumentSignalNodeProjection,
    FolderRelationshipProjection,
    FolderSignalNodeProjection,
    FolderSignalProjection,
)


def replace_document_projection(
    session: Any,
    *,
    relationships: DocumentRelationshipProjection,
    signals: DocumentSignalProjection,
) -> None:
    _replace_document_relationships(session, relationships)
    _replace_document_signals(session, signals)


def _replace_document_relationships(
    session: Any,
    projection: DocumentRelationshipProjection,
) -> None:
    _merge_document_relationship_identity(session, projection)


def replace_document_folder_relations(
    session: Any,
    *,
    projection: DocumentFolderRelationProjection,
) -> None:
    _merge_document_reference(session, projection)
    _replace_document_folder_relation_edges(session, projection)


def _replace_document_folder_relation_edges(
    session: Any,
    projection: DocumentFolderRelationProjection,
) -> None:
    _delete_document_relationship_edges(session, projection)
    for folder_id in projection.folder_ids:
        _link_document_to_folder(session, projection, folder_id)


def _replace_document_signals(
    session: Any,
    projection: DocumentSignalProjection,
) -> None:
    _merge_document_signal_identity(session, projection)
    _delete_document_signal_edges(session, projection)
    _delete_document_signal_nodes(session, projection)
    for signal in projection.signals:
        _merge_document_signal_node(
            session,
            document_signal_record_from_projection(signal),
        )
        _link_document_to_signal(session, projection, signal)


def replace_folder_projection(
    session: Any,
    *,
    relationships: FolderRelationshipProjection,
    signals: FolderSignalProjection,
) -> None:
    _merge_folder(session, folder_node_from_projection(relationships))
    _delete_folder_parent_edges(session, relationships)
    _delete_folder_signals(session, signals)
    parent_folder_id = relationships.parent_folder_id
    for signal in signals.signals:
        _merge_folder_signal_node(
            session,
            folder_signal_record_from_projection(signal),
        )
        _link_folder_to_signal(session, signals, signal)
        _link_folder_signal_to_related_document(session, signal)
    if parent_folder_id is None:
        return
    _link_folder_to_parent(session, relationships, parent_folder_id)


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


def delete_folder_signal_projection(session: Any, *, folder_id: str) -> None:
    session.run(
        """
        MATCH (s:FolderSignal {folder_id: $folder_id})
        DETACH DELETE s
        """,
        folder_id=folder_id,
    )


def delete_folder_projection(session: Any, *, folder_id: str) -> None:
    session.run(
        """
        MATCH (f:Folder {folder_id: $folder_id})
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
    projection: DocumentRelationshipProjection | DocumentFolderRelationProjection,
) -> None:
    session.run(
        """
        MATCH (d:Document {document_id: $document_id})-[r:IN_FOLDER]->()
        DELETE r
        """,
        document_id=projection.document_id,
    )


def _delete_document_signal_edges(
    session: Any,
    projection: DocumentSignalProjection,
) -> None:
    session.run(
        """
        MATCH (d:Document {document_id: $document_id})-[r:HAS_SIGNAL]->()
        DELETE r
        """,
        document_id=projection.document_id,
    )


def _delete_document_signal_nodes(
    session: Any,
    projection: DocumentSignalProjection,
) -> None:
    session.run(
        """
        MATCH (s:DocumentSignal {document_id: $document_id})
        DETACH DELETE s
        """,
        document_id=projection.document_id,
    )


def _delete_folder_signals(
    session: Any,
    projection: FolderSignalProjection,
) -> None:
    delete_folder_signal_projection(session, folder_id=projection.folder_id)


def _delete_folder_parent_edges(
    session: Any,
    projection: FolderRelationshipProjection,
) -> None:
    session.run(
        """
        MATCH (f:Folder {folder_id: $folder_id})-[r:CHILD_OF]->()
        DELETE r
        """,
        folder_id=projection.folder_id,
    )


def _merge_document_relationship_identity(
    session: Any,
    projection: DocumentRelationshipProjection,
) -> None:
    document = document_relationship_node_from_projection(projection)
    session.run(
        """
        MERGE (d:Document {document_id: $document_id})
        SET d.tenant = $tenant,
            d.document_type = $document_type,
            d.source_version = $source_version,
            d.content_digest = $content_digest,
            d.created_at = $created_at,
            d.updated_at = $updated_at
        """,
        tenant=document.tenant,
        document_id=document.document_id,
        document_type=document.document_type,
        source_version=document.source_version,
        content_digest=document.content_digest,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def _merge_document_reference(
    session: Any,
    projection: DocumentFolderRelationProjection,
) -> None:
    session.run(
        """
        MERGE (d:Document {document_id: $document_id})
        SET d.tenant = $tenant
        """,
        tenant=projection.tenant,
        document_id=projection.document_id,
    )


def _merge_document_signal_identity(
    session: Any,
    projection: DocumentSignalProjection,
) -> None:
    document = document_signal_node_from_projection(projection)
    session.run(
        """
        MERGE (d:Document {document_id: $document_id})
        SET d.tenant = $tenant,
            d.document_type = $document_type,
            d.label = $label,
            d.source_version = $source_version,
            d.content_digest = $content_digest,
            d.created_at = $created_at,
            d.updated_at = $updated_at,
            d.metadata_json = $metadata_json
        """,
        tenant=document.tenant,
        document_id=document.document_id,
        document_type=document.document_type,
        label=document.label,
        source_version=document.source_version,
        content_digest=document.content_digest,
        created_at=document.created_at,
        updated_at=document.updated_at,
        metadata_json=document.metadata_json,
    )


def _link_document_to_folder(
    session: Any,
    projection: DocumentRelationshipProjection | DocumentFolderRelationProjection,
    folder_id: str,
) -> None:
    _merge_folder_reference(
        session,
        folder_reference_node(tenant=projection.tenant, folder_id=folder_id),
    )
    session.run(
        """
        MATCH (d:Document {document_id: $document_id})
        MATCH (f:Folder {folder_id: $folder_id})
        WHERE coalesce(f.deleted, false) = false
        MERGE (d)-[r:IN_FOLDER]->(f)
        SET r.tenant = $tenant,
            r.confidence = 1.0,
            r.source_version = $source_version,
            r.metadata_json = '{}'
        """,
        tenant=projection.tenant,
        document_id=projection.document_id,
        folder_id=folder_id,
        source_version=projection.source_version,
    )


def _merge_document_signal_node(
    session: Any,
    signal: Neo4jDocumentSignalNodeRecord,
) -> None:
    session.run(
        """
        MERGE (s:DocumentSignal {signal_id: $signal_id})
        SET s.tenant = $tenant,
            s.signal_type = $signal_type,
            s.signal_key = $signal_key,
            s.text = $text,
            s.document_id = $document_id,
            s.source_version = $source_version,
            s.content_digest = $content_digest,
            s.attributes_json = $attributes_json,
            s.confidence = $confidence,
            s.metadata_json = $metadata_json
        """,
        signal_id=signal.signal_id,
        tenant=signal.tenant,
        signal_type=signal.signal_type,
        signal_key=signal.signal_key,
        text=signal.text,
        document_id=signal.document_id,
        source_version=signal.source_version,
        content_digest=signal.content_digest,
        attributes_json=signal.attributes_json,
        confidence=signal.confidence,
        metadata_json=signal.metadata_json,
    )


def _link_document_to_signal(
    session: Any,
    projection: DocumentSignalProjection,
    signal: DocumentSignalNodeProjection,
) -> None:
    relationship = signal_relationship(projection=projection, signal=signal)
    session.run(
        """
        MATCH (d:Document {document_id: $document_id})
        MATCH (s:DocumentSignal {signal_id: $signal_id})
        MERGE (d)-[r:HAS_SIGNAL]->(s)
        SET r.tenant = $tenant,
            r.signal_id = $signal_id,
            r.confidence = $confidence,
            r.source_version = $source_version,
            r.content_digest = $content_digest,
            r.metadata_json = $metadata_json
        """,
        tenant=relationship.tenant,
        document_id=projection.document_id,
        signal_id=signal.signal_id,
        confidence=relationship.confidence,
        source_version=projection.source_version,
        content_digest=projection.content_digest,
        metadata_json=relationship.metadata_json,
    )


def _merge_folder_signal_node(
    session: Any,
    signal: Neo4jFolderSignalNodeRecord,
) -> None:
    session.run(
        """
        MERGE (s:FolderSignal {signal_id: $signal_id})
        SET s.tenant = $tenant,
            s.folder_id = $folder_id,
            s.source_version = $source_version,
            s.signal_type = $signal_type,
            s.signal_key = $signal_key,
            s.text = $text,
            s.related_document_id = $related_document_id,
            s.attributes_json = $attributes_json,
            s.confidence = $confidence,
            s.metadata_json = $metadata_json
        """,
        signal_id=signal.signal_id,
        tenant=signal.tenant,
        folder_id=signal.folder_id,
        source_version=signal.source_version,
        signal_type=signal.signal_type,
        signal_key=signal.signal_key,
        text=signal.text,
        related_document_id=signal.related_document_id,
        attributes_json=signal.attributes_json,
        confidence=signal.confidence,
        metadata_json=signal.metadata_json,
    )


def _link_folder_to_signal(
    session: Any,
    projection: FolderSignalProjection,
    signal: FolderSignalNodeProjection,
) -> None:
    relationship = folder_signal_relationship(projection=projection, signal=signal)
    session.run(
        """
        MATCH (f:Folder {folder_id: $folder_id})
        MATCH (s:FolderSignal {signal_id: $signal_id})
        MERGE (f)-[r:HAS_SIGNAL]->(s)
        SET r.tenant = $tenant,
            r.signal_id = $signal_id,
            r.confidence = $confidence,
            r.source_version = $source_version,
            r.metadata_json = $metadata_json
        """,
        tenant=relationship.tenant,
        folder_id=projection.folder_id,
        signal_id=signal.signal_id,
        confidence=relationship.confidence,
        source_version=projection.source_version,
        metadata_json=relationship.metadata_json,
    )


def _link_folder_signal_to_related_document(
    session: Any,
    signal: FolderSignalNodeProjection,
) -> None:
    if signal.related_document_id is None:
        return
    session.run(
        """
        MATCH (s:FolderSignal {signal_id: $signal_id})
        MATCH (d:Document {document_id: $document_id})
        MERGE (s)-[r:ABOUT_DOCUMENT]->(d)
        SET r.tenant = $tenant,
            r.confidence = $confidence,
            r.metadata_json = '{}'
        """,
        tenant=signal.tenant,
        signal_id=signal.signal_id,
        document_id=signal.related_document_id,
        confidence=signal.confidence if signal.confidence is not None else 1.0,
    )


def _link_folder_to_parent(
    session: Any,
    projection: FolderRelationshipProjection,
    parent_folder_id: str,
) -> None:
    _merge_folder_reference(
        session,
        folder_reference_node(tenant=projection.tenant, folder_id=parent_folder_id),
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


def _merge_folder(session: Any, folder: Neo4jFolderNodeRecord) -> None:
    session.run(
        """
        MERGE (f:Folder {folder_id: $folder_id})
        SET f.tenant = $tenant,
            f.label = $label,
            f.path_snapshot = $path_snapshot,
            f.parent_folder_id = $parent_folder_id,
            f.created_at = $created_at,
            f.updated_at = $updated_at,
            f.metadata_json = $metadata_json,
            f.deleted = false
        FOREACH (_ IN CASE WHEN $source_version IS NULL THEN [] ELSE [1] END |
            SET f.source_version = $source_version
        )
        """,
        tenant=folder.tenant,
        folder_id=folder.folder_id,
        label=folder.label,
        path_snapshot=folder.path_snapshot,
        parent_folder_id=folder.parent_folder_id,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
        source_version=folder.source_version,
        metadata_json=folder.metadata_json,
    )


def _merge_folder_reference(session: Any, folder: Neo4jFolderNodeRecord) -> None:
    session.run(
        """
        MERGE (f:Folder {folder_id: $folder_id})
        ON CREATE SET f.tenant = $tenant,
                      f.deleted = false
        SET f.tenant = coalesce(f.tenant, $tenant),
            f.deleted = coalesce(f.deleted, false)
        """,
        tenant=folder.tenant,
        folder_id=folder.folder_id,
    )
