from __future__ import annotations

import json
import unittest
from dataclasses import replace
from pathlib import Path
from typing import TypeAlias

from foldmind_ai_core.adapters.inbound.messaging.consumers.document_chunk_vector_consumer import (
    DocumentChunkVectorDeletedConsumer,
)
from foldmind_ai_core.adapters.inbound.messaging.consumers.document_signal_vector_consumer import (
    DocumentSignalVectorsDeletedConsumer,
    DocumentSignalVectorsIndexedConsumer,
)
from foldmind_ai_core.adapters.inbound.messaging.consumers.document_vector_consumer import (
    DocumentVectorIndexedConsumer,
)
from foldmind_ai_core.adapters.inbound.messaging.consumers.folder_signal_vector_consumer import (
    FolderSignalVectorsDeletedConsumer,
    FolderSignalVectorsIndexedConsumer,
    FolderSignalVectorsInvalidatedConsumer,
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
    FolderSignalsGraphIndexedConsumer,
    FolderSignalsGraphInvalidatedConsumer,
)
from foldmind_ai_core.adapters.inbound.messaging.dispatcher import OutboxEventDispatcher
from foldmind_ai_core.adapters.inbound.messaging.message_codec import (
    delete_document_projection_command_from_outbox,
    delete_folder_projection_command_from_outbox,
    project_document_command_from_outbox,
    project_document_folder_relations_command_from_outbox,
    project_folder_command_from_outbox,
    outbox_event_from_flattened_payload,
)
from foldmind_ai_core.core.application.models.projection_commands import (
    DeleteDocumentProjectionCommand,
    DeleteFolderProjectionCommand,
    InvalidateFolderSignalsCommand,
    ProjectDocumentCommand,
    ProjectDocumentFolderRelationsCommand,
    ProjectFolderCommand,
    ProjectFolderSignalsCommand,
)
from foldmind_ai_core.core.application.mappers.outbox_events import (
    document_deleted_event,
    document_folder_relations_indexed_event,
    document_indexed_event,
    folder_deleted_event,
    folder_indexed_event,
    folder_signals_indexed_event,
    folder_signals_invalidated_event,
)
from foldmind_ai_core.core.application.models.indexing import FolderSignalInvalidation
from foldmind_ai_core.core.application.models.vector_projection import VectorProjectionSpec
from foldmind_ai_core.core.domain.models.document_chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.document_index_state import DocumentIndexState
from foldmind_ai_core.core.domain.models.document_signals import (
    DocumentSignal,
    DocumentSignalEvidence,
    DocumentSignalType,
)
from foldmind_ai_core.core.domain.models.folder_signals import (
    FolderSignal,
    FolderSignalType,
)
from foldmind_ai_core.core.domain.models.document_folder_relations import (
    SourceDocumentFolderRelationSnapshot,
)
from foldmind_ai_core.core.domain.models.document_sources import SourceDocument
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder
from foldmind_ai_core.core.domain.services.document_signal_service import DocumentSignalService
from foldmind_ai_core.core.domain.services.folder_signal_service import FolderSignalService

ProjectionCommand: TypeAlias = (
    DeleteDocumentProjectionCommand
    | DeleteFolderProjectionCommand
    | InvalidateFolderSignalsCommand
    | ProjectDocumentFolderRelationsCommand
    | ProjectDocumentCommand
    | ProjectFolderCommand
    | ProjectFolderSignalsCommand
)


class FakeProjectionConsumer:
    def __init__(self) -> None:
        self.events: list[ProjectionCommand] = []

    async def project_document_chunks(self, event: ProjectionCommand) -> None:
        self.events.append(event)

    async def delete_document_chunks(self, event: ProjectionCommand) -> None:
        self.events.append(event)

    async def project_document_vector(self, event: ProjectionCommand) -> None:
        self.events.append(event)

    async def delete_document_vector(self, event: ProjectionCommand) -> None:
        self.events.append(event)

    async def project_document_signals(self, event: ProjectionCommand) -> None:
        self.events.append(event)

    async def delete_document_signals(self, event: ProjectionCommand) -> None:
        self.events.append(event)

    async def project_folder_vector(self, event: ProjectionCommand) -> None:
        self.events.append(event)

    async def delete_folder_vector(self, event: ProjectionCommand) -> None:
        self.events.append(event)

    async def project_folder_signals(self, event: ProjectionCommand) -> None:
        self.events.append(event)

    async def invalidate_folder_signals(self, event: ProjectionCommand) -> None:
        self.events.append(event)

    async def delete_folder_signals(self, event: ProjectionCommand) -> None:
        self.events.append(event)

    async def project_document_graph(self, event: ProjectionCommand) -> None:
        self.events.append(event)

    async def project_document_folder_relations(self, event: ProjectionCommand) -> None:
        self.events.append(event)

    async def delete_document_graph(self, event: ProjectionCommand) -> None:
        self.events.append(event)

    async def project_folder_graph(self, event: ProjectionCommand) -> None:
        self.events.append(event)

    async def delete_folder_graph(self, event: ProjectionCommand) -> None:
        self.events.append(event)


class MessagingAdapterTests(unittest.IsolatedAsyncioTestCase):
    def test_outbox_domain_partition_key_uses_source_identity(self) -> None:
        event = document_deleted_event(
            tenant="tenant-1",
            document_id="doc-1",
            source_version="v1",
        )

        self.assertEqual(event.partition_key, "document:tenant-1:doc-1")

    def test_message_codec_decodes_event_specific_projection_commands(self) -> None:
        document_command = project_document_command_from_outbox(_document_indexed_event())
        document_relations_command = project_document_folder_relations_command_from_outbox(
            _document_folder_relations_indexed_event()
        )
        folder_command = project_folder_command_from_outbox(_folder_indexed_event())
        document_deleted = delete_document_projection_command_from_outbox(
            document_deleted_event(
                tenant="tenant-1",
                document_id="doc-1",
                source_version="v1",
                affected_folder_ids=("folder-1",),
            )
        )
        folder_deleted = delete_folder_projection_command_from_outbox(
            folder_deleted_event(
                tenant="tenant-1",
                folder_id="folder-1",
                source_version="folder-v1",
            )
        )

        self.assertIsInstance(document_command, ProjectDocumentCommand)
        self.assertIsInstance(
            document_relations_command,
            ProjectDocumentFolderRelationsCommand,
        )
        self.assertIsInstance(folder_command, ProjectFolderCommand)
        self.assertIsInstance(document_deleted, DeleteDocumentProjectionCommand)
        self.assertEqual(document_deleted.affected_folder_ids, ("folder-1",))
        self.assertEqual(document_deleted.tenant, "tenant-1")
        self.assertIsInstance(folder_deleted, DeleteFolderProjectionCommand)
        self.assertEqual(folder_deleted.tenant, "tenant-1")

    def test_message_codec_accepts_missing_document_type(self) -> None:
        event = _document_indexed_event()
        payload = json.loads(json.dumps(event.payload))
        payload["source_document"].pop("document_type")
        payload["profile"]["document_type"] = None
        payload["chunks"][0].pop("document_type")
        payload["signals"][0]["document_type"] = None

        decoded = project_document_command_from_outbox(replace(event, payload=payload))

        self.assertIsNone(decoded.document.document_type)
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
            project_document_folder_relations_command_from_outbox(
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
            project_document_command_from_outbox(replace(event, payload=concept_payload))

    def test_message_codec_rejects_blank_projection_relationship_ids(self) -> None:
        event = _document_folder_relations_indexed_event()
        relation_snapshot = dict(event.payload["folder_relation_snapshot"])
        relation_snapshot["folder_ids"] = [" "]
        payload = dict(event.payload)
        payload["folder_relation_snapshot"] = relation_snapshot

        with self.assertRaises(ValueError):
            project_document_folder_relations_command_from_outbox(
                replace(event, payload=payload)
            )

    def test_message_codec_trims_projection_relationship_ids(self) -> None:
        event = _document_folder_relations_indexed_event()
        relation_snapshot = dict(event.payload["folder_relation_snapshot"])
        relation_snapshot["folder_ids"] = [" folder-1 "]
        payload = dict(event.payload)
        payload["folder_relation_snapshot"] = relation_snapshot

        projection_event = project_document_folder_relations_command_from_outbox(
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
        document_index_payload = dict(event.payload["profile"])
        document_index_payload["document_id"] = " doc-1 "
        signals = list(event.payload["signals"])
        signal = dict(signals[0])
        signal["signal_id"] = " signal-1 "
        signals[0] = signal
        chunks = [dict(chunk) for chunk in event.payload["chunks"]]
        chunks[0]["document_id"] = " doc-1 "
        chunks[0]["chunk_id"] = " chunk-1 "
        payload = dict(event.payload)
        payload["source_document"] = source_document
        payload["profile"] = document_index_payload
        payload["signals"] = signals
        payload["chunks"] = chunks

        projection_event = project_document_command_from_outbox(
            replace(event, payload=payload)
        )

        self.assertEqual(projection_event.document.document_id, "doc-1")
        self.assertEqual(projection_event.document_index.document_id, "doc-1")
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
        projection_event = delete_document_projection_command_from_outbox(event)

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

        projection_event = project_folder_command_from_outbox(
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

        projection_event = project_document_command_from_outbox(
            replace(event, payload=payload)
        )

        self.assertEqual(projection_event.chunks[0].text, "  chunk text  ")
        self.assertEqual(projection_event.chunks[0].start_offset, 10)
        self.assertEqual(projection_event.chunks[0].end_offset, 24)

    def test_message_codec_rejects_mismatched_document_projection_identity(self) -> None:
        event = _document_indexed_event()
        document_index_payload = dict(event.payload["profile"])
        document_index_payload["document_id"] = "doc-other"
        payload = dict(event.payload)
        payload["profile"] = document_index_payload

        with self.assertRaises(ValueError):
            project_document_command_from_outbox(replace(event, payload=payload))

    def test_message_codec_rejects_mismatched_source_identity(self) -> None:
        with self.assertRaises(ValueError):
            delete_document_projection_command_from_outbox(
                replace(
                    document_deleted_event(
                        tenant="tenant-1",
                        document_id="doc-1",
                        source_version="v1",
                    ),
                    source_id="doc-other",
                )
            )

        with self.assertRaises(ValueError):
            project_folder_command_from_outbox(
                replace(_folder_indexed_event(), source_id="folder-other")
            )

    def test_message_codec_rejects_mismatched_source_kind(self) -> None:
        with self.assertRaises(ValueError):
            project_document_command_from_outbox(
                replace(_document_indexed_event(), source_kind="folder")
            )

    def test_message_codec_rejects_blank_folder_parent_id(self) -> None:
        event = _folder_indexed_event()
        source_folder = dict(event.payload["source_folder"])
        source_folder["parent_folder_id"] = " "
        payload = dict(event.payload)
        payload["source_folder"] = source_folder

        with self.assertRaises(ValueError):
            project_folder_command_from_outbox(replace(event, payload=payload))

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

    async def test_projection_target_consumers_call_their_application_services(self) -> None:
        document_vector_indexed = FakeProjectionConsumer()
        document_signal_indexed = FakeProjectionConsumer()
        document_folder_relations_indexed = FakeProjectionConsumer()
        document_chunk_deleted = FakeProjectionConsumer()
        document_signal_deleted = FakeProjectionConsumer()
        folder_vector_indexed = FakeProjectionConsumer()
        folder_signal_indexed = FakeProjectionConsumer()
        folder_signal_invalidated = FakeProjectionConsumer()
        folder_signal_deleted = FakeProjectionConsumer()
        folder_graph_deleted = FakeProjectionConsumer()
        folder_signal_graph_indexed = FakeProjectionConsumer()
        folder_signal_graph_invalidated = FakeProjectionConsumer()

        await DocumentVectorIndexedConsumer(
            service=document_vector_indexed,
        ).consume_outbox_event(_document_indexed_event())
        await DocumentSignalVectorsIndexedConsumer(
            service=document_signal_indexed,
        ).consume_outbox_event(_document_indexed_event())
        await DocumentGraphFolderRelationsIndexedConsumer(
            service=document_folder_relations_indexed,
        ).consume_outbox_event(_document_folder_relations_indexed_event())
        await DocumentChunkVectorDeletedConsumer(
            service=document_chunk_deleted,
        ).consume_outbox_event(
            document_deleted_event(
                tenant="tenant-1",
                document_id="doc-1",
                source_version="v1",
                affected_folder_ids=("folder-1",),
            )
        )
        await DocumentSignalVectorsDeletedConsumer(
            service=document_signal_deleted,
        ).consume_outbox_event(
            document_deleted_event(
                tenant="tenant-1",
                document_id="doc-1",
                source_version="v1",
                affected_folder_ids=("folder-1",),
            )
        )
        await FolderVectorIndexedConsumer(
            service=folder_vector_indexed,
        ).consume_outbox_event(_folder_indexed_event())
        await FolderSignalVectorsIndexedConsumer(
            service=folder_signal_indexed,
        ).consume_outbox_event(_folder_signals_indexed_event())
        await FolderSignalVectorsInvalidatedConsumer(
            service=folder_signal_invalidated,
        ).consume_outbox_event(_folder_signals_invalidated_event())
        await FolderSignalVectorsDeletedConsumer(
            service=folder_signal_deleted,
        ).consume_outbox_event(
            folder_deleted_event(
                tenant="tenant-1",
                folder_id="folder-1",
                source_version="folder-v1",
            )
        )
        await FolderSignalsGraphIndexedConsumer(
            service=folder_signal_graph_indexed,
        ).consume_outbox_event(_folder_signals_indexed_event())
        await FolderSignalsGraphInvalidatedConsumer(
            service=folder_signal_graph_invalidated,
        ).consume_outbox_event(_folder_signals_invalidated_event())
        await FolderGraphDeletedConsumer(
            service=folder_graph_deleted,
        ).consume_outbox_event(
            folder_deleted_event(
                tenant="tenant-1",
                folder_id="folder-1",
                source_version="folder-v1",
            )
        )

        self.assertIsInstance(document_vector_indexed.events[0], ProjectDocumentCommand)
        self.assertIsInstance(document_signal_indexed.events[0], ProjectDocumentCommand)
        self.assertIsInstance(
            document_folder_relations_indexed.events[0],
            ProjectDocumentFolderRelationsCommand,
        )
        self.assertIsInstance(
            document_chunk_deleted.events[0],
            DeleteDocumentProjectionCommand,
        )
        self.assertEqual(document_chunk_deleted.events[0].tenant, "tenant-1")
        self.assertEqual(
            document_chunk_deleted.events[0].affected_folder_ids,
            ("folder-1",),
        )
        self.assertIsInstance(
            document_signal_deleted.events[0],
            DeleteDocumentProjectionCommand,
        )
        self.assertIsInstance(folder_vector_indexed.events[0], ProjectFolderCommand)
        self.assertIsInstance(
            folder_signal_indexed.events[0],
            ProjectFolderSignalsCommand,
        )
        self.assertIsInstance(
            folder_signal_invalidated.events[0],
            InvalidateFolderSignalsCommand,
        )
        self.assertIsInstance(
            folder_signal_deleted.events[0],
            DeleteFolderProjectionCommand,
        )
        self.assertEqual(folder_signal_deleted.events[0].tenant, "tenant-1")
        self.assertIsInstance(folder_graph_deleted.events[0], DeleteFolderProjectionCommand)
        self.assertIsInstance(
            folder_signal_graph_indexed.events[0],
            ProjectFolderSignalsCommand,
        )
        self.assertIsInstance(
            folder_signal_graph_invalidated.events[0],
            InvalidateFolderSignalsCommand,
        )

    async def test_dispatcher_routes_by_outbox_event_type(self) -> None:
        document_indexed = FakeProjectionConsumer()
        document_folder_relations_indexed = FakeProjectionConsumer()
        document_deleted = FakeProjectionConsumer()
        folder_indexed = FakeProjectionConsumer()
        folder_signals_indexed = FakeProjectionConsumer()
        folder_signals_invalidated = FakeProjectionConsumer()
        folder_deleted = FakeProjectionConsumer()
        dispatcher = OutboxEventDispatcher(
            document_indexed=DocumentGraphIndexedConsumer(
                service=document_indexed,
            ),
            document_folder_relations_indexed=DocumentGraphFolderRelationsIndexedConsumer(
                service=document_folder_relations_indexed,
            ),
            document_deleted=DocumentGraphDeletedConsumer(
                service=document_deleted,
            ),
            folder_indexed=FolderGraphIndexedConsumer(
                service=folder_indexed,
            ),
            folder_signals_indexed=FolderSignalsGraphIndexedConsumer(
                service=folder_signals_indexed,
            ),
            folder_signals_invalidated=FolderSignalsGraphInvalidatedConsumer(
                service=folder_signals_invalidated,
            ),
            folder_deleted=FolderGraphDeletedConsumer(
                service=folder_deleted,
            ),
        )

        await dispatcher.consume_outbox_event(_document_indexed_event())
        await dispatcher.consume_outbox_event(_document_folder_relations_indexed_event())
        await dispatcher.consume_outbox_event(_folder_indexed_event())
        await dispatcher.consume_outbox_event(_folder_signals_indexed_event())
        await dispatcher.consume_outbox_event(_folder_signals_invalidated_event())
        await dispatcher.consume_outbox_event(
            document_deleted_event(
                tenant="tenant-1",
                document_id="doc-1",
                source_version="v1",
                affected_folder_ids=("folder-1",),
            )
        )
        await dispatcher.consume_outbox_event(
            folder_deleted_event(
                tenant="tenant-1",
                folder_id="folder-1",
                source_version="folder-v1",
            )
        )

        self.assertIsInstance(document_indexed.events[0], ProjectDocumentCommand)
        self.assertIsInstance(
            document_folder_relations_indexed.events[0],
            ProjectDocumentFolderRelationsCommand,
        )
        self.assertIsInstance(folder_indexed.events[0], ProjectFolderCommand)
        self.assertIsInstance(document_deleted.events[0], DeleteDocumentProjectionCommand)
        self.assertEqual(document_deleted.events[0].tenant, "tenant-1")
        self.assertEqual(
            document_deleted.events[0].affected_folder_ids,
            ("folder-1",),
        )
        self.assertIsInstance(
            folder_signals_indexed.events[0],
            ProjectFolderSignalsCommand,
        )
        self.assertIsInstance(
            folder_signals_invalidated.events[0],
            InvalidateFolderSignalsCommand,
        )
        self.assertIsInstance(folder_deleted.events[0], DeleteFolderProjectionCommand)
        self.assertEqual(folder_deleted.events[0].tenant, "tenant-1")

    async def test_dispatcher_skips_unconfigured_projection_targets(self) -> None:
        document_indexed = FakeProjectionConsumer()
        dispatcher = OutboxEventDispatcher(
            document_indexed=DocumentGraphIndexedConsumer(
                service=document_indexed,
            ),
            document_deleted=None,
            folder_indexed=None,
            folder_deleted=None,
        )

        await dispatcher.consume_outbox_event(_document_indexed_event())
        await dispatcher.consume_outbox_event(
            folder_deleted_event(
                tenant="tenant-1",
                folder_id="folder-1",
                source_version="folder-v1",
            )
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
        additional_fields = config["transforms.outbox.table.fields.additional.placement"]
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
        text="chunk text",
        start_offset=0,
        end_offset=10,
    )
    index_record = DocumentIndexState(
        document_id=document.document_id,
        document_index_input_digest=chunk.document_index_input_digest,
        document_signal_input_digest=chunk.document_index_input_digest,
    )
    return document_indexed_event(
        document=document,
        chunks=(chunk,),
        index_record=index_record,
        signals=(_summary_signal(document=document, chunk=chunk),),
        vector_projection_spec=VectorProjectionSpec(
            embedding_model="embedding",
            embedding_version="embedding-v1",
            index_schema_version="schema-v1",
        ),
        chunking_version="chunking-test-v1",
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
    return DocumentSignalService().create(
        tenant=document.tenant,
        document_type=document.document_type,
        document_id=document.document_id,
        source_version=document.source_version,
        document_signal_input_digest=chunk.document_index_input_digest,
        signal_type=DocumentSignalType.SUMMARY,
        text="Summary",
        attributes={},
        evidence=(DocumentSignalEvidence(chunk_id=chunk.chunk_id, quote=chunk.text),),
        confidence=0.8,
        extractor_name="test",
        extractor_version="v1",
    )


def _folder_indexed_event():
    return folder_indexed_event(folder=_source_folder())


def _folder_signals_indexed_event():
    folder = _source_folder()
    return folder_signals_indexed_event(
        folder=folder,
        folder_signal_input_digest="folder-signal-input-v1",
        signal_generation_version="folder-signals-v1",
        signals=(_folder_signal(folder),),
    )


def _folder_signals_invalidated_event():
    return folder_signals_invalidated_event(
        FolderSignalInvalidation(
            tenant="tenant-1",
            folder_id="folder-1",
            folder_signal_input_digest="folder-signal-input-v1",
            signal_generation_version="folder-signals-v1",
        )
    )


def _source_folder() -> SourceFolder:
    return SourceFolder(
        tenant="tenant-1",
        folder_id="folder-1",
        source_version="folder-v1",
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        name="Startup",
        parent_folder_id="root",
    )


def _folder_signal(folder: SourceFolder) -> FolderSignal:
    return FolderSignalService().create(
        tenant=folder.tenant,
        folder_id=folder.folder_id,
        source_version=folder.source_version,
        folder_signal_input_digest="folder-signal-input-v1",
        signal_generation_version="folder-signals-v1",
        signal_type=FolderSignalType.RESPONSIBILITY,
        signal_key="startup",
        text="Owns startup notes.",
        related_document_id="doc-1",
        attributes={},
        evidence=({"document_id": "doc-1", "quote": "chunk text"},),
        confidence=0.7,
        extractor_name="test",
        extractor_version="v1",
    )


if __name__ == "__main__":
    unittest.main()
