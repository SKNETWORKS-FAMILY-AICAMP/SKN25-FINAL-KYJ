from __future__ import annotations

import json
import unittest
from dataclasses import replace
from pathlib import Path
from typing import TypeAlias

from foldmind_ai_core.adapters.inbound.messaging.consumers.document_chunk_vector_consumer import (
    DocumentChunkVectorDeletedConsumer,
)
from foldmind_ai_core.adapters.inbound.messaging.consumers.document_vector_consumer import (
    DocumentVectorIndexedConsumer,
)
from foldmind_ai_core.adapters.inbound.messaging.consumers.folder_vector_consumer import (
    FolderVectorIndexedConsumer,
)
from foldmind_ai_core.adapters.inbound.messaging.consumers.graph_consumer import (
    DocumentGraphDeletedConsumer,
    DocumentGraphFolderRelationsIndexedConsumer,
    DocumentGraphIndexedConsumer,
    FolderGraphDeletedConsumer,
    FolderGraphIndexedConsumer,
)
from foldmind_ai_core.adapters.inbound.messaging.dispatcher import OutboxEventDispatcher
from foldmind_ai_core.adapters.inbound.messaging.message_codec import (
    document_deleted_event_from_outbox,
    document_folder_relations_indexed_event_from_outbox,
    document_indexed_event_from_outbox,
    folder_deleted_event_from_outbox,
    folder_indexed_event_from_outbox,
    outbox_event_from_flattened_payload,
)
from foldmind_ai_core.core.application.commands.projection import (
    DeleteDocumentProjectionCommand,
    DeleteFolderProjectionCommand,
    ProjectDocumentFolderRelationsCommand,
    ProjectDocumentCommand,
    ProjectFolderCommand,
)
from foldmind_ai_core.core.application.models.indexing import (
    SourceDocumentFolderRelationSnapshot,
)
from foldmind_ai_core.core.application.services.outbox_events import (
    document_deleted_event,
    document_folder_relations_indexed_event,
    document_indexed_event,
    folder_deleted_event,
    folder_indexed_event,
)
from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.adapters.inbound.messaging.projection_events import (
    DocumentDeletedProjectionEvent,
    DocumentFolderRelationsIndexedProjectionEvent,
    DocumentIndexedProjectionEvent,
    FolderDeletedProjectionEvent,
    FolderIndexedProjectionEvent,
)
from foldmind_ai_core.core.domain.models.profiling import (
    DocumentSignal,
    DocumentSignalType,
    DocumentProfile,
    SignalEvidence,
)
from foldmind_ai_core.core.domain.models.reference.documents import SourceDocument
from foldmind_ai_core.core.domain.models.reference.folders import SourceFolder
from foldmind_ai_core.core.domain.services.profiling import (
    create_document_signal,
)

ProjectionEvent: TypeAlias = (
    DocumentDeletedProjectionEvent
    | DocumentFolderRelationsIndexedProjectionEvent
    | DocumentIndexedProjectionEvent
    | FolderDeletedProjectionEvent
    | FolderIndexedProjectionEvent
    | DeleteDocumentProjectionCommand
    | DeleteFolderProjectionCommand
    | ProjectDocumentFolderRelationsCommand
    | ProjectDocumentCommand
    | ProjectFolderCommand
)


class FakeProjectionConsumer:
    def __init__(self) -> None:
        self.events: list[ProjectionEvent] = []

    def execute(self, event: ProjectionEvent) -> None:
        self.events.append(event)


class MessagingAdapterTests(unittest.TestCase):
    def test_outbox_domain_partition_key_uses_source_identity(self) -> None:
        event = document_deleted_event(
            tenant="tenant-1",
            document_id="doc-1",
        )

        self.assertEqual(event.partition_key, "document:tenant-1:doc-1")

    def test_message_codec_decodes_event_specific_projection_events(self) -> None:
        document_event = document_indexed_event_from_outbox(_document_indexed_event())
        document_relations_event = document_folder_relations_indexed_event_from_outbox(
            _document_folder_relations_indexed_event()
        )
        folder_event = folder_indexed_event_from_outbox(_folder_indexed_event())
        document_deleted = document_deleted_event_from_outbox(
            document_deleted_event(
                tenant="tenant-1",
                document_id="doc-1",
                affected_folder_ids=("folder-1",),
            )
        )
        folder_deleted = folder_deleted_event_from_outbox(
            folder_deleted_event(tenant="tenant-1", folder_id="folder-1")
        )

        self.assertIsInstance(document_event, DocumentIndexedProjectionEvent)
        self.assertIsInstance(
            document_relations_event,
            DocumentFolderRelationsIndexedProjectionEvent,
        )
        self.assertIsInstance(folder_event, FolderIndexedProjectionEvent)
        self.assertIsInstance(document_deleted, DocumentDeletedProjectionEvent)
        self.assertEqual(document_deleted.affected_folder_ids, ("folder-1",))
        self.assertIsInstance(folder_deleted, FolderDeletedProjectionEvent)

    def test_message_codec_accepts_missing_document_type(self) -> None:
        event = _document_indexed_event()
        payload = json.loads(json.dumps(event.payload))
        payload["source_document"].pop("document_type")
        payload["profile"]["document_type"] = None
        payload["chunks"][0].pop("document_type")
        payload["signals"][0]["document_type"] = None

        decoded = document_indexed_event_from_outbox(replace(event, payload=payload))

        self.assertIsNone(decoded.document.document_type)
        self.assertIsNone(decoded.profile.document_type)
        self.assertIsNone(decoded.chunks[0].document_type)
        self.assertIsNone(decoded.signals[0].document_type)

    def test_message_codec_decodes_flattened_debezium_outbox_message(self) -> None:
        payload = {
            "event_id": "11111111-1111-4111-8111-111111111111",
            "event_sequence": 12,
            "tenant_id": "tenant-1",
            "partition_key": "document:tenant-1:doc-1",
            "source_kind": "document",
            "source_id": "doc-1",
            "event_type": "DOCUMENT_DELETED",
            "payload_schema_version": 1,
            "idempotency_key": "document-delete:tenant-1:doc-1",
            "payload": json.dumps(
                {
                    "tenant": "tenant-1",
                    "document_id": "doc-1",
                    "affected_folder_ids": ["folder-1"],
                }
            ),
        }

        event = outbox_event_from_flattened_payload(json.dumps(payload).encode("utf-8"))

        self.assertEqual(event.event_id, "11111111-1111-4111-8111-111111111111")
        self.assertEqual(event.event_sequence, 12)
        self.assertEqual(event.partition_key, "document:tenant-1:doc-1")
        self.assertEqual(event.event_type, "DOCUMENT_DELETED")
        self.assertEqual(event.tenant, "tenant-1")
        self.assertEqual(event.payload["document_id"], "doc-1")
        self.assertEqual(event.payload["affected_folder_ids"], ["folder-1"])

    def test_message_codec_rejects_unsupported_payload_schema_version(self) -> None:
        payload = {
            "event_id": "11111111-1111-4111-8111-111111111111",
            "event_sequence": 12,
            "tenant_id": "tenant-1",
            "partition_key": "document:tenant-1:doc-1",
            "source_kind": "document",
            "source_id": "doc-1",
            "event_type": "DOCUMENT_DELETED",
            "payload_schema_version": 2,
            "idempotency_key": "document-delete:tenant-1:doc-1",
            "payload": {
                "tenant": "tenant-1",
                "document_id": "doc-1",
            },
        }

        with self.assertRaises(ValueError):
            outbox_event_from_flattened_payload(payload)

    def test_message_codec_rejects_noncanonical_flattened_field_names(self) -> None:
        payload = {
            "id": "11111111-1111-4111-8111-111111111111",
            "tenantId": "tenant-1",
            "eventKey": "DOCUMENT:tenant-1:doc-1",
            "aggregateType": "DOCUMENT",
            "aggregateId": "doc-1",
            "eventType": "DOCUMENT_DELETED",
            "eventSchemaVersion": "1",
            "idempotencyKey": "document-delete:tenant-1:doc-1",
            "payload": {
                "tenant": "tenant-1",
                "document_id": "doc-1",
            },
        }

        with self.assertRaises(ValueError):
            outbox_event_from_flattened_payload(payload)

    def test_message_codec_rejects_malformed_projection_payload_types(self) -> None:
        event = _document_folder_relations_indexed_event()
        relation_snapshot = dict(event.payload["folder_relation_snapshot"])
        relation_snapshot["folder_ids"] = ["folder-1", None]
        payload = dict(event.payload)
        payload["folder_relation_snapshot"] = relation_snapshot

        with self.assertRaises(ValueError):
            document_folder_relations_indexed_event_from_outbox(
                replace(event, payload=payload)
            )

    def test_message_codec_rejects_out_of_range_signal_confidence(self) -> None:
        event = _document_indexed_event()
        signals = list(event.payload["signals"])
        signal = dict(signals[0])
        signal["confidence"] = float("nan")
        signals[0] = signal
        concept_payload = dict(event.payload)
        concept_payload["signals"] = signals

        with self.assertRaises(ValueError):
            document_indexed_event_from_outbox(replace(event, payload=concept_payload))

    def test_message_codec_rejects_blank_projection_relationship_ids(self) -> None:
        event = _document_folder_relations_indexed_event()
        relation_snapshot = dict(event.payload["folder_relation_snapshot"])
        relation_snapshot["folder_ids"] = [" "]
        payload = dict(event.payload)
        payload["folder_relation_snapshot"] = relation_snapshot

        with self.assertRaises(ValueError):
            document_folder_relations_indexed_event_from_outbox(
                replace(event, payload=payload)
            )

    def test_message_codec_trims_projection_relationship_ids(self) -> None:
        event = _document_folder_relations_indexed_event()
        relation_snapshot = dict(event.payload["folder_relation_snapshot"])
        relation_snapshot["folder_ids"] = [" folder-1 "]
        payload = dict(event.payload)
        payload["folder_relation_snapshot"] = relation_snapshot

        projection_event = document_folder_relations_indexed_event_from_outbox(
            replace(event, payload=payload)
        )

        self.assertEqual(
            projection_event.folder_relation_snapshot.folder_ids,
            ("folder-1",),
        )

    def test_message_codec_trims_required_projection_identity_fields(self) -> None:
        event = _document_indexed_event()
        source_document = dict(event.payload["source_document"])
        source_document["document_id"] = " doc-1 "
        profile = dict(event.payload["profile"])
        profile["document_id"] = " doc-1 "
        signals = list(event.payload["signals"])
        signal = dict(signals[0])
        signal["signal_id"] = " signal-1 "
        signals[0] = signal
        chunks = [dict(chunk) for chunk in event.payload["chunks"]]
        chunks[0]["document_id"] = " doc-1 "
        chunks[0]["chunk_id"] = " chunk-1 "
        payload = dict(event.payload)
        payload["source_document"] = source_document
        payload["profile"] = profile
        payload["signals"] = signals
        payload["chunks"] = chunks

        projection_event = document_indexed_event_from_outbox(
            replace(event, payload=payload)
        )

        self.assertEqual(projection_event.document.document_id, "doc-1")
        self.assertEqual(projection_event.profile.document_id, "doc-1")
        self.assertEqual(projection_event.chunks[0].document_id, "doc-1")
        self.assertEqual(projection_event.chunks[0].chunk_id, "chunk-1")
        self.assertEqual(projection_event.signals[0].signal_id, "signal-1")

    def test_message_codec_trims_flattened_source_identity(self) -> None:
        payload = {
            "event_id": "11111111-1111-4111-8111-111111111111",
            "event_sequence": 12,
            "tenant_id": " tenant-1 ",
            "partition_key": "document:tenant-1:doc-1",
            "source_kind": "document",
            "source_id": " doc-1 ",
            "event_type": "DOCUMENT_DELETED",
            "payload_schema_version": 1,
            "idempotency_key": " document-delete:tenant-1:doc-1 ",
            "payload": {
                "tenant": " tenant-1 ",
                "document_id": " doc-1 ",
            },
        }

        event = outbox_event_from_flattened_payload(payload)
        projection_event = document_deleted_event_from_outbox(event)

        self.assertEqual(event.source_id, "doc-1")
        self.assertEqual(event.tenant, "tenant-1")
        self.assertEqual(event.partition_key, "document:tenant-1:doc-1")
        self.assertEqual(projection_event.document_id, "doc-1")
        self.assertEqual(projection_event.affected_folder_ids, ())

    def test_message_codec_preserves_source_content_fields(self) -> None:
        event = _folder_indexed_event()
        source_folder = dict(event.payload["source_folder"])
        source_folder["name"] = " Startup "
        source_folder["path"] = " /Root/Startup "
        source_folder["parent_folder_id"] = " root "
        source_folder["description"] = "   "
        payload = dict(event.payload)
        payload["source_folder"] = source_folder

        projection_event = folder_indexed_event_from_outbox(
            replace(event, payload=payload)
        )

        self.assertEqual(projection_event.folder.name, " Startup ")
        self.assertEqual(projection_event.folder.path, " /Root/Startup ")
        self.assertEqual(projection_event.folder.parent_folder_id, "root")
        self.assertEqual(projection_event.folder.description, "   ")

    def test_message_codec_preserves_chunk_text_with_matching_offsets(self) -> None:
        event = _document_indexed_event()
        chunks = [dict(chunk) for chunk in event.payload["chunks"]]
        chunks[0]["search_text"] = "  chunk text  "
        chunks[0]["source_start_offset"] = 10
        chunks[0]["source_end_offset"] = 24
        payload = dict(event.payload)
        payload["chunks"] = chunks

        projection_event = document_indexed_event_from_outbox(
            replace(event, payload=payload)
        )

        self.assertEqual(projection_event.chunks[0].text, "  chunk text  ")
        self.assertEqual(projection_event.chunks[0].start_offset, 10)
        self.assertEqual(projection_event.chunks[0].end_offset, 24)

    def test_message_codec_rejects_mismatched_document_projection_identity(self) -> None:
        event = _document_indexed_event()
        profile = dict(event.payload["profile"])
        profile["document_id"] = "doc-other"
        payload = dict(event.payload)
        payload["profile"] = profile

        with self.assertRaises(ValueError):
            document_indexed_event_from_outbox(replace(event, payload=payload))

    def test_message_codec_rejects_mismatched_source_identity(self) -> None:
        with self.assertRaises(ValueError):
            document_deleted_event_from_outbox(
                replace(
                    document_deleted_event(
                        tenant="tenant-1",
                        document_id="doc-1",
                    ),
                    source_id="doc-other",
                )
            )

        with self.assertRaises(ValueError):
            folder_indexed_event_from_outbox(
                replace(_folder_indexed_event(), source_id="folder-other")
            )

    def test_message_codec_rejects_mismatched_source_kind(self) -> None:
        with self.assertRaises(ValueError):
            document_indexed_event_from_outbox(
                replace(_document_indexed_event(), source_kind="folder")
            )

    def test_message_codec_rejects_blank_folder_parent_id(self) -> None:
        event = _folder_indexed_event()
        source_folder = dict(event.payload["source_folder"])
        source_folder["parent_folder_id"] = " "
        payload = dict(event.payload)
        payload["source_folder"] = source_folder

        with self.assertRaises(ValueError):
            folder_indexed_event_from_outbox(replace(event, payload=payload))

    def test_message_codec_rejects_malformed_flattened_envelope_types(self) -> None:
        payload = {
            "event_id": "11111111-1111-4111-8111-111111111111",
            "event_sequence": "12",
            "tenant_id": "tenant-1",
            "partition_key": "document:tenant-1:doc-1",
            "source_kind": "document",
            "source_id": "doc-1",
            "event_type": "DOCUMENT_DELETED",
            "payload_schema_version": 1,
            "idempotency_key": "document-delete:tenant-1:doc-1",
            "payload": {
                "tenant": "tenant-1",
                "document_id": "doc-1",
            },
        }

        with self.assertRaises(ValueError):
            outbox_event_from_flattened_payload(payload)

    def test_projection_target_consumers_call_their_use_cases(self) -> None:
        document_indexed = FakeProjectionConsumer()
        document_folder_relations_indexed = FakeProjectionConsumer()
        document_deleted = FakeProjectionConsumer()
        folder_indexed = FakeProjectionConsumer()
        folder_deleted = FakeProjectionConsumer()

        DocumentVectorIndexedConsumer(
            use_case=document_indexed,
        ).consume_outbox_event(_document_indexed_event())
        DocumentGraphFolderRelationsIndexedConsumer(
            use_case=document_folder_relations_indexed,
        ).consume_outbox_event(_document_folder_relations_indexed_event())
        DocumentChunkVectorDeletedConsumer(
            use_case=document_deleted,
        ).consume_outbox_event(
            document_deleted_event(
                tenant="tenant-1",
                document_id="doc-1",
                affected_folder_ids=("folder-1",),
            )
        )
        FolderVectorIndexedConsumer(
            use_case=folder_indexed,
        ).consume_outbox_event(_folder_indexed_event())
        FolderGraphDeletedConsumer(
            use_case=folder_deleted,
        ).consume_outbox_event(
            folder_deleted_event(tenant="tenant-1", folder_id="folder-1")
        )

        self.assertIsInstance(document_indexed.events[0], ProjectDocumentCommand)
        self.assertIsInstance(
            document_folder_relations_indexed.events[0],
            ProjectDocumentFolderRelationsCommand,
        )
        self.assertIsInstance(document_deleted.events[0], DeleteDocumentProjectionCommand)
        self.assertEqual(
            document_deleted.events[0].affected_folder_ids,
            ("folder-1",),
        )
        self.assertIsInstance(folder_indexed.events[0], ProjectFolderCommand)
        self.assertIsInstance(folder_deleted.events[0], DeleteFolderProjectionCommand)

    def test_dispatcher_routes_by_outbox_event_type(self) -> None:
        document_indexed = FakeProjectionConsumer()
        document_folder_relations_indexed = FakeProjectionConsumer()
        document_deleted = FakeProjectionConsumer()
        folder_indexed = FakeProjectionConsumer()
        folder_deleted = FakeProjectionConsumer()
        dispatcher = OutboxEventDispatcher(
            document_indexed=DocumentGraphIndexedConsumer(
                use_case=document_indexed,
            ),
            document_folder_relations_indexed=DocumentGraphFolderRelationsIndexedConsumer(
                use_case=document_folder_relations_indexed,
            ),
            document_deleted=DocumentGraphDeletedConsumer(
                use_case=document_deleted,
            ),
            folder_indexed=FolderGraphIndexedConsumer(
                use_case=folder_indexed,
            ),
            folder_deleted=FolderGraphDeletedConsumer(
                use_case=folder_deleted,
            ),
        )

        dispatcher.consume_outbox_event(_document_indexed_event())
        dispatcher.consume_outbox_event(_document_folder_relations_indexed_event())
        dispatcher.consume_outbox_event(_folder_indexed_event())
        dispatcher.consume_outbox_event(
            document_deleted_event(
                tenant="tenant-1",
                document_id="doc-1",
                affected_folder_ids=("folder-1",),
            )
        )
        dispatcher.consume_outbox_event(
            folder_deleted_event(tenant="tenant-1", folder_id="folder-1")
        )

        self.assertIsInstance(document_indexed.events[0], ProjectDocumentCommand)
        self.assertIsInstance(
            document_folder_relations_indexed.events[0],
            ProjectDocumentFolderRelationsCommand,
        )
        self.assertIsInstance(folder_indexed.events[0], ProjectFolderCommand)
        self.assertIsInstance(document_deleted.events[0], DeleteDocumentProjectionCommand)
        self.assertEqual(
            document_deleted.events[0].affected_folder_ids,
            ("folder-1",),
        )
        self.assertIsInstance(folder_deleted.events[0], DeleteFolderProjectionCommand)

    def test_dispatcher_skips_unconfigured_projection_targets(self) -> None:
        document_indexed = FakeProjectionConsumer()
        dispatcher = OutboxEventDispatcher(
            document_indexed=DocumentGraphIndexedConsumer(
                use_case=document_indexed,
            ),
            document_deleted=None,
            folder_indexed=None,
            folder_deleted=None,
        )

        dispatcher.consume_outbox_event(_document_indexed_event())
        dispatcher.consume_outbox_event(
            folder_deleted_event(tenant="tenant-1", folder_id="folder-1")
        )

        self.assertEqual(len(document_indexed.events), 1)

    def test_debezium_example_uses_partition_key_and_indexing_topic(self) -> None:
        config = json.loads(
            Path("examples/debezium/outbox-connector.json").read_text(encoding="utf-8")
        )["config"]

        self.assertEqual(config["table.include.list"], "public.outbox_events")
        self.assertEqual(
            config["transforms.outbox.table.field.event.key"],
            "partition_key",
        )
        self.assertEqual(
            config["transforms.outbox.route.topic.replacement"],
            "indexing-events",
        )
        additional_fields = config[
            "transforms.outbox.table.fields.additional.placement"
        ]
        self.assertIn("event_sequence:envelope", additional_fields)
        self.assertIn("partition_key:envelope", additional_fields)
        self.assertIn("tenant_id:envelope", additional_fields)
        self.assertIn("source_kind:envelope", additional_fields)
        self.assertIn("source_id:envelope", additional_fields)
        self.assertIn("idempotency_key:envelope", additional_fields)
        self.assertNotIn("created_at:envelope", additional_fields)


def _document_indexed_event():
    document = SourceDocument(
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        source_version="v1",
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        title="MVP memo",
        body="Original body",
    )
    chunk = DocumentChunk(
        tenant=document.tenant,
        document_type=document.document_type,
        document_id=document.document_id,
        source_version=document.source_version,
        document_index_input_digest="index-input-v1",
        created_at=document.created_at,
        updated_at=document.updated_at,
        chunk_id="chunk-1",
        chunk_index=0,
        chunking_version="chunking-test-v1",
        text="chunk text",
        text_hash="hash-1",
        start_offset=0,
        end_offset=10,
        embedding_model="embedding",
        embedding_version="embedding-v1",
        index_schema_version="schema-v1",
    )
    profile = DocumentProfile(
        tenant=document.tenant,
        document_type=document.document_type,
        document_id=document.document_id,
        source_version=document.source_version,
        created_at=document.created_at,
        updated_at=document.updated_at,
        title=document.title,
        document_index_input_digest=chunk.document_index_input_digest,
        document_signal_input_digest=chunk.document_index_input_digest,
    )
    return document_indexed_event(
        document=document,
        chunks=(chunk,),
        profile=profile,
        signals=(_summary_signal(document=document, chunk=chunk),),
    )


def _document_folder_relations_indexed_event():
    return document_folder_relations_indexed_event(
        SourceDocumentFolderRelationSnapshot(
            tenant="tenant-1",
            document_id="doc-1",
            source_version="v2",
            folder_ids=("folder-2",),
        )
    )


def _summary_signal(
    *,
    document: SourceDocument,
    chunk: DocumentChunk,
) -> DocumentSignal:
    return create_document_signal(
        tenant=document.tenant,
        document_type=document.document_type,
        document_id=document.document_id,
        source_version=document.source_version,
        document_signal_input_digest=chunk.document_index_input_digest,
        signal_type=DocumentSignalType.SUMMARY,
        text="Summary",
        attributes={},
        evidence=(SignalEvidence(chunk_id=chunk.chunk_id, quote=chunk.text),),
        confidence=0.8,
        extractor_name="test",
        extractor_version="v1",
    )


def _folder_indexed_event():
    return folder_indexed_event(
        folder=SourceFolder(
            tenant="tenant-1",
            folder_id="folder-1",
            source_version="folder-v1",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
            name="Startup",
            parent_folder_id="root",
        )
    )

if __name__ == "__main__":
    unittest.main()
