from __future__ import annotations

import json
import unittest
from pathlib import Path

from foldmind_ai_core.adapters.inbound.messaging.consumer import (
    DocumentChunkVectorDeletedConsumer,
    DocumentGraphDeletedConsumer,
    DocumentGraphIndexedConsumer,
    DocumentVectorIndexedConsumer,
    FolderGraphDeletedConsumer,
    FolderGraphIndexedConsumer,
    FolderVectorIndexedConsumer,
)
from foldmind_ai_core.adapters.inbound.messaging.dispatcher import OutboxEventDispatcher
from foldmind_ai_core.adapters.inbound.messaging.message_codec import (
    document_deleted_event_from_outbox,
    document_indexed_event_from_outbox,
    folder_deleted_event_from_outbox,
    folder_indexed_event_from_outbox,
    outbox_event_from_flattened_payload,
    outbox_event_key,
)
from foldmind_ai_core.application.services.outbox_events import (
    document_deleted_event,
    document_indexed_event,
    folder_deleted_event,
    folder_indexed_event,
)
from foldmind_ai_core.domain.indexing.chunks import DocumentChunk
from foldmind_ai_core.domain.indexing.projection_events import (
    DocumentDeletedProjectionEvent,
    DocumentIndexedProjectionEvent,
    FolderDeletedProjectionEvent,
    FolderIndexedProjectionEvent,
)
from foldmind_ai_core.domain.profiling.concepts import profile_concepts_from_labels
from foldmind_ai_core.domain.profiling.models import DocumentProfile
from foldmind_ai_core.domain.reference.documents import SourceDocument
from foldmind_ai_core.domain.reference.folders import SourceFolder


class FakeProjectionHandler:
    def __init__(self) -> None:
        self.events: list[object] = []

    def handle(self, event: object) -> None:
        self.events.append(event)


class MessagingAdapterTests(unittest.TestCase):
    def test_outbox_event_key_uses_aggregate_identity(self) -> None:
        event = document_deleted_event(document_id="doc-1")

        self.assertEqual(outbox_event_key(event), "DOCUMENT:doc-1")

    def test_message_codec_decodes_event_specific_projection_events(self) -> None:
        document_event = document_indexed_event_from_outbox(_document_indexed_event())
        folder_event = folder_indexed_event_from_outbox(_folder_indexed_event())
        document_deleted = document_deleted_event_from_outbox(
            document_deleted_event(document_id="doc-1")
        )
        folder_deleted = folder_deleted_event_from_outbox(
            folder_deleted_event(folder_id="folder-1")
        )

        self.assertIsInstance(document_event, DocumentIndexedProjectionEvent)
        self.assertIsInstance(folder_event, FolderIndexedProjectionEvent)
        self.assertIsInstance(document_deleted, DocumentDeletedProjectionEvent)
        self.assertIsInstance(folder_deleted, FolderDeletedProjectionEvent)

    def test_message_codec_decodes_flattened_debezium_outbox_message(self) -> None:
        payload = {
            "id": "11111111-1111-4111-8111-111111111111",
            "sequence": 12,
            "event_key": "DOCUMENT:doc-1",
            "aggregate_type": "DOCUMENT",
            "aggregate_id": "doc-1",
            "event_type": "DOCUMENT_DELETED",
            "event_schema_version": "1",
            "payload": json.dumps(
                {
                    "document_id": "doc-1",
                }
            ),
        }

        event = outbox_event_from_flattened_payload(json.dumps(payload).encode("utf-8"))

        self.assertEqual(event.id, "11111111-1111-4111-8111-111111111111")
        self.assertEqual(event.sequence, 12)
        self.assertEqual(outbox_event_key(event), "DOCUMENT:doc-1")
        self.assertEqual(event.event_type, "DOCUMENT_DELETED")
        self.assertEqual(event.payload["document_id"], "doc-1")

    def test_projection_target_consumers_call_their_use_cases(self) -> None:
        document_indexed = FakeProjectionHandler()
        document_deleted = FakeProjectionHandler()
        folder_indexed = FakeProjectionHandler()
        folder_deleted = FakeProjectionHandler()

        DocumentVectorIndexedConsumer(
            use_case=document_indexed,  # type: ignore[arg-type]
        ).handle_outbox_event(_document_indexed_event())
        DocumentChunkVectorDeletedConsumer(
            use_case=document_deleted,  # type: ignore[arg-type]
        ).handle_outbox_event(document_deleted_event(document_id="doc-1"))
        FolderVectorIndexedConsumer(
            use_case=folder_indexed,  # type: ignore[arg-type]
        ).handle_outbox_event(_folder_indexed_event())
        FolderGraphDeletedConsumer(
            use_case=folder_deleted,  # type: ignore[arg-type]
        ).handle_outbox_event(folder_deleted_event(folder_id="folder-1"))

        self.assertIsInstance(document_indexed.events[0], DocumentIndexedProjectionEvent)
        self.assertIsInstance(document_deleted.events[0], DocumentDeletedProjectionEvent)
        self.assertIsInstance(folder_indexed.events[0], FolderIndexedProjectionEvent)
        self.assertIsInstance(folder_deleted.events[0], FolderDeletedProjectionEvent)

    def test_dispatcher_routes_by_outbox_event_type(self) -> None:
        document_indexed = FakeProjectionHandler()
        document_deleted = FakeProjectionHandler()
        folder_indexed = FakeProjectionHandler()
        folder_deleted = FakeProjectionHandler()
        dispatcher = OutboxEventDispatcher(
            document_indexed=DocumentGraphIndexedConsumer(
                use_case=document_indexed,  # type: ignore[arg-type]
            ),
            document_deleted=DocumentGraphDeletedConsumer(
                use_case=document_deleted,  # type: ignore[arg-type]
            ),
            folder_indexed=FolderGraphIndexedConsumer(
                use_case=folder_indexed,  # type: ignore[arg-type]
            ),
            folder_deleted=FolderGraphDeletedConsumer(
                use_case=folder_deleted,  # type: ignore[arg-type]
            ),
        )

        dispatcher.handle_outbox_event(_document_indexed_event())
        dispatcher.handle_outbox_event(_folder_indexed_event())
        dispatcher.handle_outbox_event(
            document_deleted_event(document_id="doc-1")
        )
        dispatcher.handle_outbox_event(
            folder_deleted_event(folder_id="folder-1")
        )

        self.assertIsInstance(document_indexed.events[0], DocumentIndexedProjectionEvent)
        self.assertIsInstance(folder_indexed.events[0], FolderIndexedProjectionEvent)
        self.assertIsInstance(document_deleted.events[0], DocumentDeletedProjectionEvent)
        self.assertIsInstance(folder_deleted.events[0], FolderDeletedProjectionEvent)

    def test_debezium_example_uses_event_key_and_indexing_topic(self) -> None:
        config = json.loads(
            Path("examples/debezium/outbox-connector.json").read_text(encoding="utf-8")
        )["config"]

        self.assertEqual(config["table.include.list"], "public.outbox_events")
        self.assertEqual(
            config["transforms.outbox.table.field.event.key"],
            "event_key",
        )
        self.assertEqual(
            config["transforms.outbox.route.topic.replacement"],
            "indexing-events",
        )
        additional_fields = config[
            "transforms.outbox.table.fields.additional.placement"
        ]
        self.assertIn("sequence:envelope", additional_fields)
        self.assertIn("event_key:envelope", additional_fields)


def _document_indexed_event():
    document = SourceDocument(
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        source_version="v1",
        title="MVP memo",
        body="Original body",
        folder_ids=("folder-1",),
        tag_ids=("tag-1",),
    )
    chunk = DocumentChunk(
        tenant=document.tenant,
        document_type=document.document_type,
        document_id=document.document_id,
        source_version=document.source_version,
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
        title=document.title,
        summary="Summary",
        profile_version="profile-v1",
        profile_schema_version="profile-schema-v1",
        concepts=profile_concepts_from_labels(
            tenant=document.tenant,
            labels=("startup",),
        ),
    )
    return document_indexed_event(document=document, chunks=(chunk,), profile=profile)


def _folder_indexed_event():
    return folder_indexed_event(
        folder=SourceFolder(
            tenant="tenant-1",
            folder_id="folder-1",
            source_version="folder-v1",
            name="Startup",
            parent_folder_id="root",
        )
    )

if __name__ == "__main__":
    unittest.main()
