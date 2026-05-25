from __future__ import annotations

import unittest
from dataclasses import replace

from foldmind_ai_core.adapters.inbound.messaging.message_codec import (
    delete_document_projection_command_from_outbox,
    project_document_command_from_outbox,
    project_folder_command_from_outbox,
    project_folder_signals_command_from_outbox,
    invalidate_folder_signals_command_from_outbox,
)
from foldmind_ai_core.core.application.models.projection_commands import (
    ProjectDocumentCommand,
    ProjectFolderCommand,
    ProjectFolderSignalsCommand,
    InvalidateFolderSignalsCommand,
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
from foldmind_ai_core.core.domain.models.outbox import OutboxEvent
from foldmind_ai_core.core.domain.models.document_index_state import (
    DocumentIndexState,
)
from foldmind_ai_core.core.domain.models.document_signals import (
    DocumentSignal,
    DocumentSignalEvidence,
    DocumentSignalType,
)
from foldmind_ai_core.core.domain.models.folder_signals import (
    FolderSignalType,
)
from foldmind_ai_core.core.domain.models.document_sources import SourceDocument
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder
from foldmind_ai_core.core.domain.models.document_folder_relations import (
    SourceDocumentFolderRelationSnapshot,
)
from foldmind_ai_core.core.domain.services.document_signal_service import (
    DocumentSignalService,
)
from foldmind_ai_core.core.domain.services.folder_signal_service import FolderSignalService
from foldmind_ai_core.shared.validation import InvalidInputError


def _vector_projection_spec() -> VectorProjectionSpec:
    return VectorProjectionSpec(
        embedding_model="embedding",
        embedding_version="v1",
        index_schema_version="schema-v1",
    )


def _summary_signal(
    *,
    source: SourceDocument,
    chunk: DocumentChunk,
) -> DocumentSignal:
    return DocumentSignalService().create(
        tenant=source.tenant,
        document_type=source.document_type,
        document_id=source.document_id,
        source_version=source.source_version,
        document_signal_input_digest=chunk.document_index_input_digest,
        signal_type=DocumentSignalType.SUMMARY,
        text="Summary",
        attributes={},
        evidence=(DocumentSignalEvidence(chunk_id=chunk.chunk_id, quote=chunk.text),),
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
            document_index_input_digest="index-input-v1",
            created_at=source.created_at,
            updated_at=source.updated_at,
            chunk_id="chunk-1",
            chunk_index=0,
            text="chunk text",
            start_offset=0,
            end_offset=10,
        )
        index_record = DocumentIndexState(
            document_id=source.document_id,
            document_index_input_digest=chunk.document_index_input_digest,
            document_signal_input_digest=chunk.document_index_input_digest,
        )
        signals = (_summary_signal(source=source, chunk=chunk),)

        event = document_indexed_event(
            document=source,
            chunks=(chunk,),
            index_record=index_record,
            signals=signals,
            vector_projection_spec=_vector_projection_spec(),
            chunking_version="chunking-test-v1",
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
        decoded = project_document_command_from_outbox(event)
        self.assertIsInstance(decoded, ProjectDocumentCommand)
        assert isinstance(decoded, ProjectDocumentCommand)
        self.assertEqual(decoded.document.created_at, source.created_at)
        self.assertEqual(decoded.document.updated_at, source.updated_at)
        self.assertEqual(
            decoded.document_index.document_id,
            index_record.document_id,
        )
        self.assertEqual(
            decoded.document.created_at,
            source.created_at,
        )
        self.assertEqual(
            decoded.document.updated_at,
            source.updated_at,
        )
        self.assertEqual(decoded.signals[0].signal_id, signals[0].signal_id)
        self.assertEqual(decoded.signals[0].signal_type, "summary")
        self.assertEqual(event.payload["chunks"][0]["search_text"], "chunk text")
        self.assertEqual(
            event.payload["chunks"][0]["chunking_version"],
            "chunking-test-v1",
        )
        self.assertNotIn("concepts", event.payload["profile"])
        self.assertEqual(event.payload["signals"][0]["text"], "Summary")
        self.assertEqual(event.payload["source_document"]["created_at"], source.created_at)
        self.assertEqual(event.payload["source_document"]["updated_at"], source.updated_at)
        self.assertNotIn("folder_relation_snapshot", event.payload)
        self.assertEqual(event.payload["chunks"][0]["created_at"], source.created_at)
        self.assertEqual(event.payload["chunks"][0]["updated_at"], source.updated_at)
        self.assertEqual(
            event.payload["chunks"][0]["document_index_input_digest"],
            chunk.document_index_input_digest,
        )
        self.assertEqual(
            event.payload["profile"]["document_index_input_digest"],
            chunk.document_index_input_digest,
        )
        self.assertEqual(
            event.payload["signals"][0]["document_signal_input_digest"],
            chunk.document_index_input_digest,
        )
        self.assertEqual(
            event.payload["profile"]["created_at"],
            source.created_at,
        )
        self.assertEqual(
            event.payload["profile"]["updated_at"],
            source.updated_at,
        )

    def test_document_event_rejects_mismatched_index_record_context(self) -> None:
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
            document_index_input_digest="index-input-v1",
            created_at=source.created_at,
            updated_at=source.updated_at,
            chunk_id="chunk-1",
            chunk_index=0,
            text="chunk text",
            start_offset=0,
            end_offset=10,
        )
        index_record = DocumentIndexState(
            document_id="other-doc",
            document_index_input_digest=chunk.document_index_input_digest,
            document_signal_input_digest=chunk.document_index_input_digest,
        )

        with self.assertRaises(InvalidInputError):
            document_indexed_event(
                document=source,
                chunks=(chunk,),
                index_record=index_record,
                signals=(_summary_signal(source=source, chunk=chunk),),
                vector_projection_spec=_vector_projection_spec(),
                chunking_version="chunking-test-v1",
            )

        with self.assertRaises(InvalidInputError):
            document_indexed_event(
                document=source,
                chunks=(chunk,),
                index_record=replace(
                    index_record,
                    document_id=source.document_id,
                    document_signal_input_digest=" ",
                ),
                signals=(),
                vector_projection_spec=_vector_projection_spec(),
                chunking_version="chunking-test-v1",
            )

        with self.assertRaises(InvalidInputError):
            document_indexed_event(
                document=source,
                chunks=(),
                index_record=replace(
                    index_record,
                    document_id=source.document_id,
                ),
                signals=(),
                vector_projection_spec=_vector_projection_spec(),
                chunking_version="chunking-test-v1",
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
            source_version="v3",
            affected_folder_ids=("folder-1", "folder-2"),
        )

        self.assertEqual(event.event_type, "DOCUMENT_DELETED")
        self.assertEqual(event.idempotency_key, "document-delete:tenant-1:doc-1:v3")
        self.assertEqual(
            event.payload,
            {
                "tenant": "tenant-1",
                "document_id": "doc-1",
                "affected_folder_ids": ["folder-1", "folder-2"],
            },
        )
        decoded = delete_document_projection_command_from_outbox(event)
        self.assertEqual(decoded.tenant, "tenant-1")
        self.assertEqual(decoded.affected_folder_ids, ("folder-1", "folder-2"))

    def test_delete_event_idempotency_is_scoped_to_source_version_without_payload_change(
        self,
    ) -> None:
        first = document_deleted_event(
            tenant="tenant-1",
            document_id="doc-1",
            source_version="v1",
        )
        second = document_deleted_event(
            tenant="tenant-1",
            document_id="doc-1",
            source_version="v2",
        )
        folder = folder_deleted_event(
            tenant="tenant-1",
            folder_id="folder-1",
            source_version="folder-v1",
        )

        self.assertNotEqual(first.idempotency_key, second.idempotency_key)
        self.assertEqual(first.payload, second.payload)
        self.assertEqual(
            folder.idempotency_key,
            "folder-delete:tenant-1:folder-1:folder-v1",
        )
        self.assertEqual(
            folder.payload,
            {
                "tenant": "tenant-1",
                "folder_id": "folder-1",
            },
        )

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
        signal = FolderSignalService().create(
            tenant="tenant-1",
            folder_id="folder-1",
            source_version="folder-v1",
            signal_type=FolderSignalType.RESPONSIBILITY,
            signal_key="responsibility",
            text="Research folder responsibility.",
            extractor_name="test",
            extractor_version="v1",
            generation_model="folder-model",
            folder_signal_input_digest="folder-signal-input-v2",
        )

        source_event = folder_indexed_event(folder=folder)
        indexed_event = folder_signals_indexed_event(
            folder=folder,
            folder_signal_input_digest="folder-signal-input-v2",
            signal_generation_version="folder-signals-v1",
            signals=(signal,),
        )
        invalidated_event = folder_signals_invalidated_event(
            FolderSignalInvalidation(
                tenant="tenant-1",
                folder_id="folder-1",
                folder_signal_input_digest="folder-signal-input-v2",
                signal_generation_version="folder-signals-v1",
            )
        )

        source_projection = project_folder_command_from_outbox(source_event)
        indexed_projection = project_folder_signals_command_from_outbox(indexed_event)
        invalidated_projection = invalidate_folder_signals_command_from_outbox(
            invalidated_event
        )

        self.assertIsInstance(source_projection, ProjectFolderCommand)
        self.assertIsInstance(indexed_projection, ProjectFolderSignalsCommand)
        self.assertIsInstance(
            invalidated_projection,
            InvalidateFolderSignalsCommand,
        )
        self.assertNotIn("signals", source_event.payload)
        self.assertEqual(indexed_event.event_type, "FOLDER_SIGNALS_INDEXED")
        self.assertEqual(
            indexed_event.payload["signals"][0]["folder_signal_input_digest"],
            "folder-signal-input-v2",
        )
        self.assertEqual(
            indexed_event.payload["signals"][0]["generation_model"],
            "folder-model",
        )
        self.assertEqual(
            invalidated_event.payload,
            {
                "tenant": "tenant-1",
                "folder_id": "folder-1",
                "folder_signal_input_digest": "folder-signal-input-v2",
                "signal_generation_version": "folder-signals-v1",
            },
        )
        self.assertEqual(indexed_projection.folder_signal_input_digest, "folder-signal-input-v2")
        self.assertEqual(
            indexed_projection.signals[0].folder_signal_input_digest, "folder-signal-input-v2"
        )
        self.assertEqual(
            invalidated_projection.folder_signal_input_digest, "folder-signal-input-v2"
        )

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

    def test_outbox_event_rejects_malformed_idempotency_key_type(self) -> None:
        with self.assertRaises(InvalidInputError):
            OutboxEvent(
                tenant="tenant-1",
                source_kind="document",
                source_id="doc-1",
                event_type="DOCUMENT_DELETED",
                idempotency_key=None,  # type: ignore[arg-type]
                payload={
                    "tenant": "tenant-1",
                    "document_id": "doc-1",
                },
            )


if __name__ == "__main__":
    unittest.main()
