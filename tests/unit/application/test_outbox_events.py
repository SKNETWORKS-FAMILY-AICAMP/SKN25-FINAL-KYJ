from __future__ import annotations

import unittest

from foldmind_ai_core.adapters.inbound.messaging.message_codec import (
    document_deleted_event_from_outbox,
    document_indexed_event_from_outbox,
    folder_indexed_event_from_outbox,
    folder_signals_indexed_event_from_outbox,
    folder_signals_invalidated_event_from_outbox,
)
from foldmind_ai_core.core.application.services.outbox_events import (
    document_deleted_event,
    document_folder_relations_indexed_event,
    document_indexed_event,
    folder_indexed_event,
    folder_signals_indexed_event,
    folder_signals_invalidated_event,
)
from foldmind_ai_core.core.application.models.indexing import (
    FolderSignalInvalidation,
    SourceDocumentFolderRelationSnapshot,
)
from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.indexing.outbox import OutboxEvent
from foldmind_ai_core.adapters.inbound.messaging.projection_events import (
    DocumentIndexedProjectionEvent,
    FolderIndexedProjectionEvent,
    FolderSignalsIndexedProjectionEvent,
    FolderSignalsInvalidatedProjectionEvent,
)
from foldmind_ai_core.core.domain.models.profiling import (
    DocumentSignal,
    DocumentSignalType,
    DocumentProfile,
    FolderSignalType,
    SignalEvidence,
)
from foldmind_ai_core.core.domain.models.reference.documents import SourceDocument
from foldmind_ai_core.core.domain.models.reference.folders import SourceFolder
from foldmind_ai_core.core.domain.services.profiling import (
    create_document_signal,
    create_folder_signal,
)
from foldmind_ai_core.shared.validation import InvalidInputError


def _summary_signal(
    *,
    source: SourceDocument,
    chunk: DocumentChunk,
) -> DocumentSignal:
    return create_document_signal(
        tenant=source.tenant,
        document_type=source.document_type,
        document_id=source.document_id,
        source_version=source.source_version,
        signal_type=DocumentSignalType.SUMMARY,
        text="Summary",
        attributes={},
        evidence=(SignalEvidence(chunk_id=chunk.chunk_id, quote=chunk.text),),
        confidence=0.8,
        extractor_name="test",
        extractor_version="v1",
    )


class OutboxEventCodecTests(unittest.TestCase):
    def test_document_event_carries_projection_input_snapshot(self) -> None:
        source = SourceDocument(
            tenant="tenant-1",
            document_type="document",
            document_id="doc-1",
            source_version="v1",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
            title="MVP memo",
            body="Original body",
            metadata={"source": "app"},
        )
        chunk = DocumentChunk(
            tenant=source.tenant,
            document_type=source.document_type,
            document_id=source.document_id,
            source_version=source.source_version,
            created_at=source.created_at,
            updated_at=source.updated_at,
            chunk_id="chunk-1",
            chunk_index=0,
            chunking_version="chunking-test-v1",
            text="chunk text",
            text_hash="hash-1",
            start_offset=0,
            end_offset=10,
            embedding_model="embedding",
            embedding_version="v1",
            index_schema_version="schema-v1",
        )
        profile = DocumentProfile(
            tenant=source.tenant,
            document_type=source.document_type,
            document_id=source.document_id,
            source_version=source.source_version,
            created_at=source.created_at,
            updated_at=source.updated_at,
            title=source.title,
            signal_generation_version="1",
        )
        signals = (_summary_signal(source=source, chunk=chunk),)

        event = document_indexed_event(
            document=source,
            chunks=(chunk,),
            profile=profile,
            signals=signals,
        )

        self.assertEqual(event.partition_key, "document:tenant-1:doc-1")
        self.assertEqual(event.tenant, "tenant-1")
        self.assertEqual(event.event_type, "DOCUMENT_INDEXED")
        self.assertEqual(
            set(event.payload),
            {
                "source_document",
                "chunks",
                "profile",
                "signals",
            },
        )
        decoded = document_indexed_event_from_outbox(event)
        self.assertIsInstance(decoded, DocumentIndexedProjectionEvent)
        assert isinstance(decoded, DocumentIndexedProjectionEvent)
        self.assertEqual(decoded.document.created_at, source.created_at)
        self.assertEqual(decoded.document.updated_at, source.updated_at)
        self.assertEqual(decoded.profile.document_id, profile.document_id)
        self.assertEqual(decoded.profile.created_at, profile.created_at)
        self.assertEqual(decoded.profile.updated_at, profile.updated_at)
        self.assertEqual(decoded.signals[0].signal_id, signals[0].signal_id)
        self.assertEqual(decoded.signals[0].signal_type, "summary")
        self.assertEqual(event.payload["chunks"][0]["text"], "chunk text")
        self.assertNotIn("concepts", event.payload["profile"])
        self.assertEqual(event.payload["signals"][0]["text"], "Summary")
        self.assertEqual(event.payload["source_document"]["created_at"], source.created_at)
        self.assertEqual(event.payload["source_document"]["updated_at"], source.updated_at)
        self.assertNotIn("folder_relation_snapshot", event.payload)
        self.assertEqual(event.payload["chunks"][0]["created_at"], chunk.created_at)
        self.assertEqual(event.payload["chunks"][0]["updated_at"], chunk.updated_at)
        self.assertEqual(event.payload["profile"]["created_at"], profile.created_at)
        self.assertEqual(event.payload["profile"]["updated_at"], profile.updated_at)

    def test_document_event_rejects_mismatched_projection_context(self) -> None:
        source = SourceDocument(
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
            tenant=source.tenant,
            document_type=source.document_type,
            document_id="doc-other",
            source_version=source.source_version,
            created_at=source.created_at,
            updated_at=source.updated_at,
            chunk_id="chunk-1",
            chunk_index=0,
            chunking_version="chunking-test-v1",
            text="chunk text",
            text_hash="hash-1",
            start_offset=0,
            end_offset=10,
            embedding_model="embedding",
            embedding_version="v1",
            index_schema_version="schema-v1",
        )
        profile = DocumentProfile(
            tenant=source.tenant,
            document_type=source.document_type,
            document_id=source.document_id,
            source_version="v2",
            created_at=source.created_at,
            updated_at=source.updated_at,
            title=source.title,
            signal_generation_version="1",
        )

        with self.assertRaises(InvalidInputError):
            document_indexed_event(
                document=source,
                chunks=(chunk,),
                profile=profile,
                signals=(_summary_signal(source=source, chunk=chunk),),
            )

    def test_document_folder_relations_event_carries_relation_snapshot(self) -> None:
        snapshot = SourceDocumentFolderRelationSnapshot(
            tenant="tenant-1",
            document_id="doc-1",
            source_version="v2",
            folder_ids=("folder-1",),
        )

        event = document_folder_relations_indexed_event(snapshot)

        self.assertEqual(event.partition_key, "document:tenant-1:doc-1")
        self.assertEqual(event.tenant, "tenant-1")
        self.assertEqual(event.event_type, "DOCUMENT_FOLDER_RELATIONS_INDEXED")
        self.assertEqual(
            event.payload["folder_relation_snapshot"],
            {
                "tenant": "tenant-1",
                "document_id": "doc-1",
                "source_version": "v2",
                "folder_ids": ["folder-1"],
            },
        )

    def test_document_deleted_event_carries_affected_folder_ids(self) -> None:
        event = document_deleted_event(
            tenant="tenant-1",
            document_id="doc-1",
            affected_folder_ids=("folder-1", "folder-2"),
        )

        self.assertEqual(event.event_type, "DOCUMENT_DELETED")
        self.assertEqual(event.idempotency_key, "document-delete:tenant-1:doc-1")
        self.assertEqual(
            event.payload,
            {
                "tenant": "tenant-1",
                "document_id": "doc-1",
                "affected_folder_ids": ["folder-1", "folder-2"],
            },
        )
        decoded = document_deleted_event_from_outbox(event)
        self.assertEqual(decoded.affected_folder_ids, ("folder-1", "folder-2"))

    def test_folder_events_split_source_and_signal_projection_payloads(self) -> None:
        folder = SourceFolder(
            tenant="tenant-1",
            folder_id="folder-1",
            source_version="folder-v1",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
            name="Research",
            path="/Research",
        )
        signal = create_folder_signal(
            tenant="tenant-1",
            folder_id="folder-1",
            source_version="folder-v1",
            signal_type=FolderSignalType.RESPONSIBILITY,
            signal_key="responsibility",
            text="Research folder responsibility.",
            extractor_name="test",
            extractor_version="v1",
            folder_signal_input_revision=2,
        )

        source_event = folder_indexed_event(folder=folder)
        indexed_event = folder_signals_indexed_event(
            folder=folder,
            folder_signal_input_revision=2,
            signals=(signal,),
        )
        invalidated_event = folder_signals_invalidated_event(
            FolderSignalInvalidation(
                tenant="tenant-1",
                folder_id="folder-1",
                folder_signal_input_revision=2,
            )
        )

        source_projection = folder_indexed_event_from_outbox(source_event)
        indexed_projection = folder_signals_indexed_event_from_outbox(indexed_event)
        invalidated_projection = folder_signals_invalidated_event_from_outbox(
            invalidated_event
        )

        self.assertIsInstance(source_projection, FolderIndexedProjectionEvent)
        self.assertIsInstance(indexed_projection, FolderSignalsIndexedProjectionEvent)
        self.assertIsInstance(
            invalidated_projection,
            FolderSignalsInvalidatedProjectionEvent,
        )
        self.assertNotIn("signals", source_event.payload)
        self.assertEqual(indexed_event.event_type, "FOLDER_SIGNALS_INDEXED")
        self.assertEqual(
            indexed_event.payload["signals"][0]["folder_signal_input_revision"],
            2,
        )
        self.assertEqual(
            invalidated_event.payload,
            {
                "tenant": "tenant-1",
                "folder_id": "folder-1",
                "folder_signal_input_revision": 2,
            },
        )
        self.assertEqual(indexed_projection.folder_signal_input_revision, 2)
        self.assertEqual(indexed_projection.signals[0].folder_signal_input_revision, 2)
        self.assertEqual(invalidated_projection.folder_signal_input_revision, 2)

    def test_outbox_payload_schema_version_stays_at_initial_version(self) -> None:
        with self.assertRaises(InvalidInputError):
            OutboxEvent(
                tenant="tenant-1",
                source_kind="document",
                source_id="doc-1",
                event_type="DOCUMENT_DELETED",
                payload_schema_version=2,
                idempotency_key="document-delete:tenant-1:doc-1",
                payload={
                    "tenant": "tenant-1",
                    "document_id": "doc-1",
                },
            )

    def test_outbox_default_idempotency_key_uses_canonical_payload(self) -> None:
        first = OutboxEvent(
            tenant="tenant-1",
            source_kind="document",
            source_id="doc-1",
            event_type="DOCUMENT_DELETED",
            payload={
                "tenant": "tenant-1",
                "document_id": "doc-1",
                "nested": {"b": 2, "a": 1},
            },
        )
        second = OutboxEvent(
            tenant="tenant-1",
            source_kind="document",
            source_id="doc-1",
            event_type="DOCUMENT_DELETED",
            payload={
                "nested": {"a": 1, "b": 2},
                "document_id": "doc-1",
                "tenant": "tenant-1",
            },
        )

        self.assertEqual(first.idempotency_key, second.idempotency_key)

    def test_outbox_event_rejects_blank_identity_fields(self) -> None:
        for field_name in ("tenant", "source_kind", "source_id", "event_type"):
            values = {
                "tenant": "tenant-1",
                "source_kind": "document",
                "source_id": "doc-1",
                "event_type": "DOCUMENT_DELETED",
            }
            values[field_name] = " "
            with self.assertRaises(InvalidInputError):
                OutboxEvent(
                    **values,
                    idempotency_key="document-delete:tenant-1:doc-1",
                    payload={
                        "tenant": "tenant-1",
                        "document_id": "doc-1",
                    },
                )

    def test_outbox_event_rejects_malformed_sequence(self) -> None:
        for event_sequence in (True, "12", 0, -1):
            with self.subTest(event_sequence=event_sequence):
                with self.assertRaises(InvalidInputError):
                    OutboxEvent(
                        tenant="tenant-1",
                        source_kind="document",
                        source_id="doc-1",
                        event_type="DOCUMENT_DELETED",
                        event_sequence=event_sequence,
                        idempotency_key="document-delete:tenant-1:doc-1",
                        payload={
                            "tenant": "tenant-1",
                            "document_id": "doc-1",
                        },
                    )


if __name__ == "__main__":
    unittest.main()
