from __future__ import annotations

from typing import Any

from foldmind_ai_core.adapters.outbound.neo4j.mappers import (
    document_relationship_node_from_source,
    document_signal_node_from_source,
    document_signal_record_from_source,
    folder_node_from_source,
    folder_reference_node,
    folder_signal_record_from_source,
    folder_signal_relationship,
    signal_relationship,
)
from foldmind_ai_core.adapters.outbound.neo4j.models import (
    Neo4jDocumentSignalNodeRecord,
    Neo4jFolderNodeRecord,
    Neo4jFolderSignalNodeRecord,
)
from foldmind_ai_core.core.domain.models.document_folder_relations import (
    SourceDocumentFolderRelationSnapshot,
)
from foldmind_ai_core.core.domain.models.document_index_state import DocumentIndexState
from foldmind_ai_core.core.domain.models.document_signals import DocumentSignal
from foldmind_ai_core.core.domain.models.document_sources import DocumentSourceState
from foldmind_ai_core.core.domain.models.folder_signals import FolderSignal
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder


def replace_document_projection(
    session: Any,
    *,
    document: DocumentSourceState,
    document_index: DocumentIndexState,
    signals: tuple[DocumentSignal, ...],
) -> None:
    _replace_document_relationships(session, document)
    _replace_document_signals(session, document, document_index, signals)


def _replace_document_relationships(
    session: Any,
    document: DocumentSourceState,
) -> None:
    _merge_document_relationship_identity(session, document)


def replace_document_folder_relations(
    session: Any,
    *,
    projection: SourceDocumentFolderRelationSnapshot,
) -> None:
    _merge_document_reference(session, projection)
    _replace_document_folder_relation_edges(session, projection)


def _replace_document_folder_relation_edges(
    session: Any,
    projection: SourceDocumentFolderRelationSnapshot,
) -> None:
    _delete_document_relationship_edges(session, projection)
    for folder_id in projection.folder_ids:
        _link_document_to_folder(session, projection, folder_id)


def _replace_document_signals(
    session: Any,
    document: DocumentSourceState,
    document_index: DocumentIndexState,
    signals: tuple[DocumentSignal, ...],
) -> None:
    _merge_document_signal_identity(session, document, document_index)
    _delete_document_signal_edges(session, document)
    _delete_document_signal_nodes(session, document)
    for signal in signals:
        _merge_document_signal_node(
            session,
            document_signal_record_from_source(
                signal,
                content_digest=document.content_digest,
            ),
        )
        _link_document_to_signal(session, document, document_index, signal)


def replace_folder_projection(
    session: Any,
    *,
    folder: SourceFolder,
) -> None:
    _merge_folder(session, folder_node_from_source(folder))
    _delete_folder_parent_edges(session, folder)
    parent_folder_id = folder.parent_folder_id
    if parent_folder_id is None:
        return
    _link_folder_to_parent(session, folder, parent_folder_id)


def replace_folder_signal_projection(
    session: Any,
    *,
    folder: SourceFolder,
    folder_signal_input_digest: str,
    signal_generation_version: str,
    signals: tuple[FolderSignal, ...],
) -> None:
    delete_folder_signal_projection(
        session,
        tenant=folder.tenant,
        folder_id=folder.folder_id,
    )
    for signal in signals:
        _merge_folder_signal_node(
            session,
            folder_signal_record_from_source(signal),
        )
        _link_folder_to_signal(
            session,
            folder,
            folder_signal_input_digest,
            signal_generation_version,
            signal,
        )
        _link_folder_signal_to_related_document(session, signal)


def delete_document_projection(
    session: Any,
    *,
    tenant: str,
    document_id: str,
) -> None:
    session.run(
        """
        MATCH (d:Document {tenant: $tenant, document_id: $document_id})
        DETACH DELETE d
        """,
        tenant=tenant,
        document_id=document_id,
    )


def delete_folder_signal_projection(
    session: Any,
    *,
    tenant: str,
    folder_id: str,
) -> None:
    session.run(
        """
        MATCH (s:FolderSignal {tenant: $tenant, folder_id: $folder_id})
        DETACH DELETE s
        """,
        tenant=tenant,
        folder_id=folder_id,
    )


def delete_stale_folder_signal_projection(
    session: Any,
    *,
    tenant: str,
    folder_id: str,
    current_folder_signal_input_digest: str,
) -> None:
    session.run(
        """
        MATCH (s:FolderSignal {tenant: $tenant, folder_id: $folder_id})
        WHERE coalesce(s.folder_signal_input_digest, '') <> $current_folder_signal_input_digest
        DETACH DELETE s
        """,
        tenant=tenant,
        folder_id=folder_id,
        current_folder_signal_input_digest=current_folder_signal_input_digest,
    )


def delete_folder_projection(session: Any, *, tenant: str, folder_id: str) -> None:
    session.run(
        """
        MATCH (f:Folder {tenant: $tenant, folder_id: $folder_id})
        SET f.projection_state = 'deleted'
        REMOVE f.deleted
        WITH f
        OPTIONAL MATCH (f)-[outgoing_child_of:CHILD_OF]->()
        DELETE outgoing_child_of
        WITH f
        OPTIONAL MATCH (f)<-[incoming_child_of:CHILD_OF]-()
        DELETE incoming_child_of
        WITH f
        OPTIONAL MATCH (:Document)-[in_folder:IN_FOLDER]->(f)
        DELETE in_folder
        WITH f
        OPTIONAL MATCH (f)-[:HAS_SIGNAL]->(s:FolderSignal)
        DETACH DELETE s
        """,
        tenant=tenant,
        folder_id=folder_id,
    )


def _delete_document_relationship_edges(
    session: Any,
    projection: SourceDocumentFolderRelationSnapshot,
) -> None:
    session.run(
        """
        MATCH (d:Document {tenant: $tenant, document_id: $document_id})-[r:IN_FOLDER]->()
        DELETE r
        """,
        tenant=projection.tenant,
        document_id=projection.document_id,
    )


def _delete_document_signal_edges(
    session: Any,
    document: DocumentSourceState,
) -> None:
    session.run(
        """
        MATCH (d:Document {tenant: $tenant, document_id: $document_id})-[r:HAS_SIGNAL]->()
        DELETE r
        """,
        tenant=document.tenant,
        document_id=document.document_id,
    )


def _delete_document_signal_nodes(
    session: Any,
    document: DocumentSourceState,
) -> None:
    session.run(
        """
        MATCH (s:DocumentSignal {tenant: $tenant, document_id: $document_id})
        DETACH DELETE s
        """,
        tenant=document.tenant,
        document_id=document.document_id,
    )


def _delete_folder_parent_edges(
    session: Any,
    folder: SourceFolder,
) -> None:
    session.run(
        """
        MATCH (f:Folder {tenant: $tenant, folder_id: $folder_id})-[r:CHILD_OF]->()
        DELETE r
        """,
        tenant=folder.tenant,
        folder_id=folder.folder_id,
    )


def _merge_document_relationship_identity(
    session: Any,
    document: DocumentSourceState,
) -> None:
    document = document_relationship_node_from_source(document)
    session.run(
        """
        MERGE (d:Document {tenant: $tenant, document_id: $document_id})
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
    projection: SourceDocumentFolderRelationSnapshot,
) -> None:
    session.run(
        """
        MERGE (d:Document {tenant: $tenant, document_id: $document_id})
        SET d.tenant = $tenant
        """,
        tenant=projection.tenant,
        document_id=projection.document_id,
    )


def _merge_document_signal_identity(
    session: Any,
    document: DocumentSourceState,
    document_index: DocumentIndexState,
) -> None:
    document = document_signal_node_from_source(document, document_index)
    session.run(
        """
        MERGE (d:Document {tenant: $tenant, document_id: $document_id})
        SET d.tenant = $tenant,
            d.document_type = $document_type,
            d.label = $label,
            d.source_version = $source_version,
            d.content_digest = $content_digest,
            d.document_index_input_digest = $document_index_input_digest,
            d.document_signal_input_digest = $document_signal_input_digest,
            d.signal_generation_version = $signal_generation_version,
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
        document_index_input_digest=document.document_index_input_digest,
        document_signal_input_digest=document.document_signal_input_digest,
        signal_generation_version=document.signal_generation_version,
        created_at=document.created_at,
        updated_at=document.updated_at,
        metadata_json=document.metadata_json,
    )


def _link_document_to_folder(
    session: Any,
    projection: SourceDocumentFolderRelationSnapshot,
    folder_id: str,
) -> None:
    _merge_folder_reference(
        session,
        folder_reference_node(tenant=projection.tenant, folder_id=folder_id),
    )
    session.run(
        """
        MATCH (d:Document {tenant: $tenant, document_id: $document_id})
        MATCH (f:Folder {tenant: $tenant, folder_id: $folder_id})
        WHERE f.projection_state <> 'deleted'
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
        MERGE (s:DocumentSignal {tenant: $tenant, signal_id: $signal_id})
        SET s.tenant = $tenant,
            s.signal_type = $signal_type,
            s.signal_key = $signal_key,
            s.text = $text,
            s.document_id = $document_id,
            s.source_version = $source_version,
            s.content_digest = $content_digest,
            s.document_signal_input_digest = $document_signal_input_digest,
            s.signal_generation_version = $signal_generation_version,
            s.attributes_json = $attributes_json,
            s.evidence_json = $evidence_json,
            s.confidence = $confidence,
            s.extractor_name = $extractor_name,
            s.extractor_version = $extractor_version,
            s.generation_model = $generation_model,
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
        document_signal_input_digest=signal.document_signal_input_digest,
        signal_generation_version=signal.signal_generation_version,
        attributes_json=signal.attributes_json,
        evidence_json=signal.evidence_json,
        confidence=signal.confidence,
        extractor_name=signal.extractor_name,
        extractor_version=signal.extractor_version,
        generation_model=signal.generation_model,
        metadata_json=signal.metadata_json,
    )


def _link_document_to_signal(
    session: Any,
    document: DocumentSourceState,
    document_index: DocumentIndexState,
    signal: DocumentSignal,
) -> None:
    relationship = signal_relationship(
        document=document,
        document_index=document_index,
        signal=signal,
    )
    session.run(
        """
        MATCH (d:Document {tenant: $tenant, document_id: $document_id})
        MATCH (s:DocumentSignal {tenant: $tenant, signal_id: $signal_id})
        MERGE (d)-[r:HAS_SIGNAL]->(s)
        SET r.tenant = $tenant,
            r.signal_id = $signal_id,
            r.confidence = $confidence,
            r.source_version = $source_version,
            r.content_digest = $content_digest,
            r.document_signal_input_digest = $document_signal_input_digest,
            r.signal_generation_version = $signal_generation_version,
            r.metadata_json = $metadata_json
        """,
        tenant=relationship.tenant,
        document_id=document.document_id,
        signal_id=signal.signal_id,
        confidence=relationship.confidence,
        source_version=document.source_version,
        content_digest=document.content_digest,
        document_signal_input_digest=document_index.document_signal_input_digest,
        signal_generation_version=document_index.signal_generation_version,
        metadata_json=relationship.metadata_json,
    )


def _merge_folder_signal_node(
    session: Any,
    signal: Neo4jFolderSignalNodeRecord,
) -> None:
    session.run(
        """
        MERGE (s:FolderSignal {tenant: $tenant, signal_id: $signal_id})
        SET s.tenant = $tenant,
            s.folder_id = $folder_id,
            s.source_version = $source_version,
            s.folder_signal_input_digest = $folder_signal_input_digest,
            s.signal_generation_version = $signal_generation_version,
            s.signal_type = $signal_type,
            s.signal_key = $signal_key,
            s.text = $text,
            s.related_document_id = $related_document_id,
            s.attributes_json = $attributes_json,
            s.evidence_json = $evidence_json,
            s.confidence = $confidence,
            s.extractor_name = $extractor_name,
            s.extractor_version = $extractor_version,
            s.generation_model = $generation_model,
            s.metadata_json = $metadata_json
        """,
        signal_id=signal.signal_id,
        tenant=signal.tenant,
        folder_id=signal.folder_id,
        source_version=signal.source_version,
        folder_signal_input_digest=signal.folder_signal_input_digest,
        signal_generation_version=signal.signal_generation_version,
        signal_type=signal.signal_type,
        signal_key=signal.signal_key,
        text=signal.text,
        related_document_id=signal.related_document_id,
        attributes_json=signal.attributes_json,
        evidence_json=signal.evidence_json,
        confidence=signal.confidence,
        extractor_name=signal.extractor_name,
        extractor_version=signal.extractor_version,
        generation_model=signal.generation_model,
        metadata_json=signal.metadata_json,
    )


def _link_folder_to_signal(
    session: Any,
    folder: SourceFolder,
    folder_signal_input_digest: str,
    signal_generation_version: str,
    signal: FolderSignal,
) -> None:
    relationship = folder_signal_relationship(
        folder=folder,
        folder_signal_input_digest=folder_signal_input_digest,
        signal_generation_version=signal_generation_version,
        signal=signal,
    )
    session.run(
        """
        MATCH (f:Folder {tenant: $tenant, folder_id: $folder_id})
        MATCH (s:FolderSignal {tenant: $tenant, signal_id: $signal_id})
        MERGE (f)-[r:HAS_SIGNAL]->(s)
        SET r.tenant = $tenant,
            r.signal_id = $signal_id,
            r.confidence = $confidence,
            r.source_version = $source_version,
            r.folder_signal_input_digest = $folder_signal_input_digest,
            r.signal_generation_version = $signal_generation_version,
            r.metadata_json = $metadata_json
        """,
        tenant=relationship.tenant,
        folder_id=folder.folder_id,
        signal_id=signal.signal_id,
        confidence=relationship.confidence,
        source_version=folder.source_version,
        folder_signal_input_digest=folder_signal_input_digest,
        signal_generation_version=signal_generation_version,
        metadata_json=relationship.metadata_json,
    )


def _link_folder_signal_to_related_document(
    session: Any,
    signal: FolderSignal,
) -> None:
    if signal.related_document_id is None:
        return
    session.run(
        """
        MATCH (s:FolderSignal {tenant: $tenant, signal_id: $signal_id})
        MATCH (d:Document {tenant: $tenant, document_id: $document_id})
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
    folder: SourceFolder,
    parent_folder_id: str,
) -> None:
    _merge_folder_reference(
        session,
        folder_reference_node(tenant=folder.tenant, folder_id=parent_folder_id),
    )
    session.run(
        """
        MATCH (child:Folder {tenant: $tenant, folder_id: $folder_id})
        MATCH (parent:Folder {tenant: $tenant, folder_id: $parent_folder_id})
        WHERE parent.projection_state <> 'deleted'
        MERGE (child)-[r:CHILD_OF]->(parent)
        SET r.tenant = $tenant,
            r.confidence = 1.0,
            r.metadata_json = '{}'
        """,
        tenant=folder.tenant,
        folder_id=folder.folder_id,
        parent_folder_id=parent_folder_id,
    )


def _merge_folder(session: Any, folder: Neo4jFolderNodeRecord) -> None:
    session.run(
        """
        MERGE (f:Folder {tenant: $tenant, folder_id: $folder_id})
        SET f.tenant = $tenant,
            f.label = $label,
            f.projection_state = $projection_state,
            f.folder_index_input_digest = $folder_index_input_digest,
            f.path_snapshot = $path_snapshot,
            f.parent_folder_id = $parent_folder_id,
            f.description = $description,
            f.created_at = $created_at,
            f.updated_at = $updated_at,
            f.metadata_json = $metadata_json
        REMOVE f.deleted
        FOREACH (_ IN CASE WHEN $source_version IS NULL THEN [] ELSE [1] END |
            SET f.source_version = $source_version
        )
        """,
        tenant=folder.tenant,
        folder_id=folder.folder_id,
        label=folder.label,
        projection_state=folder.projection_state,
        folder_index_input_digest=folder.folder_index_input_digest,
        path_snapshot=folder.path_snapshot,
        parent_folder_id=folder.parent_folder_id,
        description=folder.description,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
        source_version=folder.source_version,
        metadata_json=folder.metadata_json,
    )


def _merge_folder_reference(session: Any, folder: Neo4jFolderNodeRecord) -> None:
    session.run(
        """
        MERGE (f:Folder {tenant: $tenant, folder_id: $folder_id})
        ON CREATE SET f.tenant = $tenant,
                      f.projection_state = 'reference'
        SET f.tenant = coalesce(f.tenant, $tenant),
            f.projection_state = coalesce(f.projection_state, 'reference')
        REMOVE f.deleted
        """,
        tenant=folder.tenant,
        folder_id=folder.folder_id,
    )
