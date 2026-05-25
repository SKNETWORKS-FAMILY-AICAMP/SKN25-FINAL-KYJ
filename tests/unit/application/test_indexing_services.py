from __future__ import annotations

import unittest
from contextlib import asynccontextmanager
from dataclasses import dataclass

from foldmind_ai_core.core.application.models.indexing import (
    DeleteDocumentIndexCommand,
    DeleteFolderIndexCommand,
    IndexDocumentCommand,
)
from foldmind_ai_core.core.application.models.indexing import (
    DocumentSignalExtraction,
    FolderSignalInvalidation,
)
from foldmind_ai_core.core.application.services.indexing.document_indexing_service import (
    DocumentIndexingService,
)
from foldmind_ai_core.core.application.services.indexing.folder_indexing_service import (
    FolderIndexingService,
)
from foldmind_ai_core.core.application.models.vector_projection import VectorProjectionSpec
from foldmind_ai_core.core.domain.models.document_chunks import (
    DocumentChunk,
    DocumentChunkingPolicy,
    DocumentIndexingPolicy,
)
from foldmind_ai_core.core.domain.models.outbox import OutboxEvent
from foldmind_ai_core.core.domain.models.document_index_state import (
    DocumentIndexState,
)
from foldmind_ai_core.core.domain.models.folder_index_state import (
    FolderIndexState,
)
from foldmind_ai_core.core.domain.models.document_signals import (
    DocumentSignal,
    DocumentSignalEvidence,
    DocumentSignalType,
)
from foldmind_ai_core.core.domain.models.document_sources import SourceDocument
from foldmind_ai_core.core.domain.models.document_sources import DocumentSourceIdentity
from foldmind_ai_core.core.domain.models.folder_sources import (
    FolderSourceIdentity,
    SourceFolder,
)
from foldmind_ai_core.core.domain.models.document_folder_relations import (
    SourceDocumentFolderRelationSnapshot,
)
from foldmind_ai_core.core.domain.services.document_chunker import DocumentChunker
from foldmind_ai_core.core.domain.services.document_signal_service import DocumentSignalService
from foldmind_ai_core.shared.validation import InvalidInputError

TEST_CHUNKING_VERSION = "chunking-test-v1"
TEST_EMBEDDING_MODEL = "embedding-test-model"
TEST_EMBEDDING_VERSION = "embedding-test-v1"
TEST_INDEX_SCHEMA_VERSION = "index-schema-test-v1"


@dataclass(frozen=True, slots=True)
class FolderRelationState:
    previous_folder_ids: tuple[str, ...] = ()
    current_folder_ids: tuple[str, ...] = ()


def make_document_indexing_policy(
    *,
    chunk_size: int = 1200,
    chunk_overlap: int = 120,
) -> DocumentIndexingPolicy:
    return DocumentIndexingPolicy(
        chunking=DocumentChunkingPolicy(
            chunking_version=TEST_CHUNKING_VERSION,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        ),
        index_schema_version=TEST_INDEX_SCHEMA_VERSION,
    )


def make_vector_projection_spec() -> VectorProjectionSpec:
    return VectorProjectionSpec(
        embedding_model=TEST_EMBEDDING_MODEL,
        embedding_version=TEST_EMBEDDING_VERSION,
        index_schema_version=TEST_INDEX_SCHEMA_VERSION,
    )


class FakeIndexingWriteSession:
    def __init__(self) -> None:
        self.document_sources = self
        self.folder_sources = self
        self.document_projections = self
        self.document_relations = self
        self.folder_projections = self
        self.outbox = self
        self.document_indexes: list[DocumentIndexState] = []
        self.document_chunks: list[DocumentChunk] = []
        self.document_signals: list[DocumentSignal] = []
        self.folder_indexes: list[SourceFolder] = []
        self.folder_signals: list[object] = []
        self.deleted_documents: list[str] = []
        self.events: list[OutboxEvent] = []
        self.operations: list[str] = []
        self.document_source_is_current = True
        self.folder_source_is_current = True
        self.folder_relation = FolderRelationState()
        self.folder_source_delete_target = FolderSourceIdentity(
            tenant="tenant-1",
            folder_id="folder-1",
            source_version="folder-source-v1",
        )
        self.folder_ancestor_ids: tuple[str, ...] = ("folder-1",)
        self.folder_signal_refresh_applied = True

    async def upsert_document_source(self, document: SourceDocument) -> bool:
        self.operations.append("upsert_document_source")
        return self.document_source_is_current

    async def replace_document_projection(
        self,
        *,
        document: SourceDocument,
        chunks: tuple[DocumentChunk, ...],
        index_record: DocumentIndexState,
        signals: tuple[DocumentSignal, ...],
    ) -> None:
        self.document_indexes.append(index_record)
        self.document_chunks = list(chunks)
        self.document_signals = list(signals)
        self.operations.append("replace_document_projection")

    async def get_folder_ids_for_document(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> tuple[str, ...]:
        self.operations.append("get_folder_ids_for_document")
        if "replace_document_folder_relation_snapshot" in self.operations:
            return self.folder_relation.current_folder_ids
        if self.folder_relation.previous_folder_ids:
            return self.folder_relation.previous_folder_ids
        return ()

    async def replace_folder_relations_for_document(
        self,
        *,
        snapshot: SourceDocumentFolderRelationSnapshot,
    ) -> None:
        self.operations.append("replace_document_folder_relation_snapshot")

    async def current_document_source_identity_for_update(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> DocumentSourceIdentity | None:
        self.operations.append("current_document_source_identity_for_update")
        if document_id == "missing-doc":
            return None
        return DocumentSourceIdentity(
            tenant=tenant,
            document_id=document_id,
            source_version="v1",
        )

    async def document_identity_for_delete(
        self,
        document_id: str,
    ) -> DocumentSourceIdentity | None:
        self.deleted_documents.append(document_id)
        self.operations.append("document_identity_for_delete")
        return DocumentSourceIdentity(
            tenant="tenant-1",
            document_id=document_id,
            source_version="source-v1",
        )

    async def folder_ids_with_signals_referencing_document(
        self,
        *,
        document_id: str,
    ) -> tuple[str, ...]:
        self.operations.append("folder_ids_with_signals_referencing_document")
        return ("folder-1",)

    async def ancestor_folder_ids(
        self,
        *,
        tenant: str,
        folder_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        self.operations.append("ancestor_folder_ids")
        if folder_ids == ("folder-1",):
            return self.folder_ancestor_ids
        return tuple(sorted(set(folder_ids)))

    async def mark_document_projection_deleted(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        self.operations.append("mark_document_projection_deleted")

    async def delete_for_document(self, *, tenant: str, document_id: str) -> None:
        self.operations.append("delete_document_relations")

    async def mark_document_source_deleted(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        self.operations.append("mark_document_source_deleted")

    async def get_current_folder_source(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> SourceFolder | None:
        self.operations.append("get_current_folder_source")
        return None

    async def upsert_folder_source(self, folder: SourceFolder) -> bool:
        self.operations.append("upsert_folder_source")
        return self.folder_source_is_current

    async def active_folder_ids_in_subtree(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> tuple[str, ...]:
        self.operations.append("active_folder_ids_in_subtree")
        return (folder_id,)

    async def document_ids_for_folders(
        self,
        *,
        tenant: str,
        folder_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        self.operations.append("document_ids_for_folders")
        return ()

    async def get_current_document_sources(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
    ) -> tuple[object, ...]:
        self.operations.append("get_current_document_sources")
        return ()

    async def get_current_document_index_records(
        self,
        *,
        document_ids: tuple[str, ...],
    ) -> tuple[DocumentIndexState, ...]:
        self.operations.append("get_current_document_index_records")
        return ()

    async def current_folder_signal_generation_version(
        self,
        *,
        folder_id: str,
    ) -> str:
        self.operations.append("current_folder_signal_generation_version")
        return "1"

    async def upsert_folder_index_record(
        self,
        *,
        record: FolderIndexState,
    ) -> None:
        self.operations.append("upsert_folder_index_record")

    async def delete_folder_signals_for_folder_ids(
        self,
        *,
        folder_ids: tuple[str, ...],
    ) -> None:
        self.operations.append("delete_folder_signals_for_folder_ids")

    async def mark_folder_signals_pending(
        self,
        *,
        record: FolderIndexState,
    ) -> bool:
        self.operations.append("mark_folder_signals_pending")
        return True

    async def current_folder_signal_input_digest(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> str | None:
        self.operations.append("current_folder_signal_input_digest")
        return "folder-signal-input-v1"

    async def replace_folder_signals(
        self,
        *,
        folder: SourceFolder,
        signals: tuple[object, ...],
        expected_folder_signal_input_digest: str,
        signal_generation_version: str,
    ) -> bool:
        self.folder_indexes.append(folder)
        self.operations.append("replace_folder_signals")
        if self.folder_signal_refresh_applied:
            self.folder_signals = list(signals)
        return self.folder_signal_refresh_applied

    async def folder_identity_for_delete(
        self,
        folder_id: str,
    ) -> FolderSourceIdentity | None:
        self.operations.append("folder_identity_for_delete")
        return self.folder_source_delete_target

    async def mark_folder_projection_deleted(self, *, tenant: str, folder_id: str) -> None:
        self.operations.append("mark_folder_projection_deleted")

    async def mark_folder_source_deleted(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> None:
        self.operations.append("mark_folder_source_deleted")

    async def append(self, event: OutboxEvent) -> None:
        self.events.append(event)
        self.operations.append("append_outbox")


class FakeIndexingWriteSessionProvider:
    def __init__(self) -> None:
        self.tx = FakeIndexingWriteSession()
        self.opened = 0

    @asynccontextmanager
    async def transaction(self):
        self.opened += 1
        yield self.tx


class FakeDocumentSignalExtractor:
    async def extract(
        self,
        document: SourceDocument,
        chunks: list[DocumentChunk],
    ) -> DocumentSignalExtraction:
        index_record = DocumentIndexState(
            document_id=document.document_id,
            document_index_input_digest=chunks[0].document_index_input_digest,
            document_signal_input_digest=chunks[0].document_index_input_digest,
        )
        signal = DocumentSignalService().create(
            tenant=document.tenant,
            document_type=document.document_type,
            document_id=document.document_id,
            source_version=document.source_version,
            document_signal_input_digest=chunks[0].document_index_input_digest,
            signal_type=DocumentSignalType.SUMMARY,
            text="Document summary",
            attributes={},
            evidence=(
                DocumentSignalEvidence(
                    chunk_id=chunks[0].chunk_id,
                    quote=chunks[0].text,
                ),
            ),
            confidence=0.8,
            extractor_name="fake_signal_extractor",
            extractor_version="test-v1",
            generation_model="fake-model",
        )
        return DocumentSignalExtraction(
            index_record=index_record,
            signals=(signal,),
        )


def make_document(
    *,
    body: str = "body",
    document_type: str | None = "document",
) -> SourceDocument:
    return SourceDocument(
        tenant="tenant-1",
        document_type=document_type,
        document_id="doc-1",
        source_version="v1",
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        title="",
        body=body,
    )


def make_index_document_command(
    *,
    body: str = "body",
    folder_ids: tuple[str, ...] | None = None,
) -> IndexDocumentCommand:
    return IndexDocumentCommand(
        document=SourceDocument(
            tenant="tenant-1",
            document_type="document",
            document_id="doc-1",
            source_version="v1",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
            title="",
            body=body,
        ),
        folder_ids=folder_ids,
    )


def make_folder() -> SourceFolder:
    return SourceFolder(
        tenant="tenant-1",
        folder_id="folder-1",
        source_version="folder-v1",
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        name="Research",
        path="/Research",
        description="Research notes",
    )


def make_index_document_service(
    *,
    indexing: FakeIndexingWriteSessionProvider | None = None,
    chunk_size: int = 1200,
    chunk_overlap: int = 120,
) -> DocumentIndexingService:
    return DocumentIndexingService(
        signal_extractor=FakeDocumentSignalExtractor(),
        indexing=indexing or FakeIndexingWriteSessionProvider(),
        chunker=DocumentChunker(make_document_indexing_policy(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )),
        vector_projection_spec=make_vector_projection_spec(),
    )


class IndexingApplicationServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_document_indexing_deletes_projection_and_publishes_outbox_event(
        self,
    ) -> None:
        indexing = FakeIndexingWriteSessionProvider()

        result = await make_index_document_service(
            indexing=indexing,
        ).index_document(make_index_document_command(body=" "))

        self.assertEqual(result.indexed_chunk_count, 0)
        self.assertEqual(indexing.tx.deleted_documents, ["doc-1"])
        self.assertEqual(
            [event.event_type for event in indexing.tx.events],
            ["DOCUMENT_DELETED", "FOLDER_SIGNALS_INVALIDATED"],
        )
        self.assertEqual(indexing.tx.events[0].source_id, "doc-1")
        self.assertEqual(indexing.tx.events[0].tenant, "tenant-1")
        self.assertEqual(
            indexing.tx.events[0].payload["affected_folder_ids"],
            ["folder-1"],
        )
        self.assertEqual(
            indexing.tx.operations,
            [
                "upsert_document_source",
                "document_identity_for_delete",
                "get_folder_ids_for_document",
                "folder_ids_with_signals_referencing_document",
                "ancestor_folder_ids",
                "mark_document_projection_deleted",
                "delete_document_relations",
                "mark_document_source_deleted",
                "delete_folder_signals_for_folder_ids",
                "get_current_folder_source",
                "current_folder_signal_generation_version",
                "active_folder_ids_in_subtree",
                "document_ids_for_folders",
                "get_current_document_sources",
                "get_current_document_index_records",
                "mark_folder_signals_pending",
                "append_outbox",
                "append_outbox",
            ],
        )

    async def test_stale_empty_document_indexing_does_not_delete_current_index(
        self,
    ) -> None:
        indexing = FakeIndexingWriteSessionProvider()
        indexing.tx.document_source_is_current = False

        result = await make_index_document_service(
            indexing=indexing,
        ).index_document(make_index_document_command(body=" "))

        self.assertEqual(result.indexed_chunk_count, 0)
        self.assertEqual(indexing.tx.deleted_documents, [])
        self.assertEqual([event.event_type for event in indexing.tx.events], [])
        self.assertEqual(
            indexing.tx.operations,
            ["upsert_document_source"],
        )

    async def test_explicit_document_delete_deletes_projection_and_publishes_outbox_event(
        self,
    ) -> None:
        indexing = FakeIndexingWriteSessionProvider()

        await DocumentIndexingService(
            indexing=indexing,
            signal_extractor=FakeDocumentSignalExtractor(),
            chunker=DocumentChunker(make_document_indexing_policy()),
            vector_projection_spec=make_vector_projection_spec(),
        ).delete_document(
            DeleteDocumentIndexCommand(
                document_id="doc-1",
            )
        )

        self.assertEqual(indexing.tx.deleted_documents, ["doc-1"])
        self.assertEqual(
            [event.event_type for event in indexing.tx.events],
            ["DOCUMENT_DELETED", "FOLDER_SIGNALS_INVALIDATED"],
        )
        self.assertEqual(
            indexing.tx.events[0].payload["affected_folder_ids"],
            ["folder-1"],
        )
        self.assertEqual(
            indexing.tx.events[0].partition_key,
            "document:tenant-1:doc-1",
        )
        self.assertEqual(
            indexing.tx.events[0].idempotency_key,
            "document-delete:tenant-1:doc-1:source-v1",
        )

    async def test_document_indexing_writes_projection_and_event_in_same_transaction(
        self,
    ) -> None:
        indexing = FakeIndexingWriteSessionProvider()

        result = await make_index_document_service(
            indexing=indexing,
        ).index_document(make_index_document_command())

        self.assertEqual(result.indexed_chunk_count, 1)
        self.assertEqual(len(indexing.tx.document_indexes), 1)
        self.assertEqual(len(indexing.tx.document_chunks), 1)
        self.assertEqual(
            [event.event_type for event in indexing.tx.events],
            ["DOCUMENT_INDEXED"],
        )
        self.assertEqual(
            indexing.tx.events[0].payload["chunks"][0]["search_text"],
            "body",
        )
        self.assertEqual(len(indexing.tx.document_signals), 1)
        self.assertEqual(
            indexing.tx.events[0].payload["signals"][0]["text"],
            "Document summary",
        )
        self.assertEqual(
            indexing.tx.operations,
            [
                "upsert_document_source",
                "replace_document_projection",
                "get_folder_ids_for_document",
                "ancestor_folder_ids",
                "append_outbox",
            ],
        )

    async def test_stale_document_indexing_does_not_publish_outbox_or_invalidate_folders(
        self,
    ) -> None:
        indexing = FakeIndexingWriteSessionProvider()
        indexing.tx.document_source_is_current = False

        result = await make_index_document_service(
            indexing=indexing,
        ).index_document(make_index_document_command())

        self.assertEqual(result.indexed_chunk_count, 0)
        self.assertEqual([event.event_type for event in indexing.tx.events], [])
        self.assertEqual(
            indexing.tx.operations,
            ["upsert_document_source"],
        )

    async def test_document_indexing_with_relation_snapshot_publishes_relation_event(
        self,
    ) -> None:
        indexing = FakeIndexingWriteSessionProvider()
        indexing.tx.folder_relation = FolderRelationState(
            previous_folder_ids=("old-folder",),
            current_folder_ids=("new-folder",),
        )

        await make_index_document_service(indexing=indexing).index_document(
            make_index_document_command(
                folder_ids=("new-folder",),
            )
        )

        self.assertEqual(
            [event.event_type for event in indexing.tx.events],
            [
                "DOCUMENT_INDEXED",
                "DOCUMENT_FOLDER_RELATIONS_INDEXED",
                "FOLDER_SIGNALS_INVALIDATED",
                "FOLDER_SIGNALS_INVALIDATED",
            ],
        )
        self.assertEqual(
            [event.source_id for event in indexing.tx.events[2:]],
            ["new-folder", "old-folder"],
        )

    async def test_folder_source_indexing_splits_source_and_signal_invalidation_events(
        self,
    ) -> None:
        indexing = FakeIndexingWriteSessionProvider()
        result = await FolderIndexingService(indexing=indexing).index_folder(
            make_folder()
        )

        self.assertEqual(result.folder_id, "folder-1")
        self.assertEqual(
            [event.event_type for event in indexing.tx.events],
            ["FOLDER_INDEXED", "FOLDER_SIGNALS_INVALIDATED"],
        )
        self.assertNotIn("signals", indexing.tx.events[0].payload)
        self.assertEqual(indexing.tx.events[1].payload["tenant"], "tenant-1")
        self.assertEqual(indexing.tx.events[1].payload["folder_id"], "folder-1")
        self.assertTrue(indexing.tx.events[1].payload["folder_signal_input_digest"])
        self.assertEqual(indexing.tx.events[1].payload["signal_generation_version"], "1")

    async def test_explicit_folder_delete_publishes_version_scoped_outbox_event(
        self,
    ) -> None:
        indexing = FakeIndexingWriteSessionProvider()

        await FolderIndexingService(indexing=indexing).delete_folder(
            DeleteFolderIndexCommand(folder_id="folder-1")
        )

        self.assertEqual(
            [event.event_type for event in indexing.tx.events],
            ["FOLDER_DELETED"],
        )
        self.assertEqual(
            indexing.tx.events[0].idempotency_key,
            "folder-delete:tenant-1:folder-1:folder-source-v1",
        )

    async def test_explicit_folder_delete_invalidates_ancestor_folder_signals(
        self,
    ) -> None:
        indexing = FakeIndexingWriteSessionProvider()
        indexing.tx.folder_source_delete_target = FolderSourceIdentity(
            tenant="tenant-1",
            folder_id="folder-1",
            source_version="folder-source-v1",
        )
        indexing.tx.folder_ancestor_ids = ("folder-1", "parent-folder")

        await FolderIndexingService(indexing=indexing).delete_folder(
            DeleteFolderIndexCommand(folder_id="folder-1")
        )

        self.assertEqual(
            [event.event_type for event in indexing.tx.events],
            ["FOLDER_DELETED", "FOLDER_SIGNALS_INVALIDATED"],
        )
        self.assertEqual(indexing.tx.events[1].source_id, "parent-folder")
        self.assertEqual(
            indexing.tx.operations,
            [
                "folder_identity_for_delete",
                "ancestor_folder_ids",
                "mark_folder_projection_deleted",
                "mark_folder_source_deleted",
                "delete_folder_signals_for_folder_ids",
                "get_current_folder_source",
                "current_folder_signal_generation_version",
                "active_folder_ids_in_subtree",
                "document_ids_for_folders",
                "get_current_document_sources",
                "get_current_document_index_records",
                "mark_folder_signals_pending",
                "append_outbox",
                "append_outbox",
            ],
        )

    def test_document_chunker_validates_config_and_preserves_offsets(self) -> None:
        chunks = DocumentChunker(
            make_document_indexing_policy(
                chunk_size=4,
                chunk_overlap=1,
            )
        ).chunk(make_document(body="abcdefg"))

        self.assertEqual([chunk.text for chunk in chunks], ["abcd", "defg", "g"])
        self.assertTrue(chunks[0].document_index_input_digest)
        self.assertEqual(
            [(chunk.start_offset, chunk.end_offset) for chunk in chunks],
            [(0, 4), (3, 7), (6, 7)],
        )
        with self.assertRaises(InvalidInputError):
            DocumentChunkingPolicy(
                chunking_version=TEST_CHUNKING_VERSION,
                chunk_size=4,
                chunk_overlap=4,
            )
        with self.assertRaises(InvalidInputError):
            DocumentChunkingPolicy(
                chunking_version=TEST_CHUNKING_VERSION,
                chunk_size=True,
                chunk_overlap=0,
            )
        with self.assertRaises(InvalidInputError):
            DocumentChunkingPolicy(
                chunking_version=TEST_CHUNKING_VERSION,
                chunk_size=4,
                chunk_overlap=False,
            )
        with self.assertRaises(InvalidInputError):
            DocumentChunkingPolicy(
                chunking_version=None,  # type: ignore[arg-type]
            )

    def test_document_chunker_offsets_match_trimmed_chunk_text(self) -> None:
        chunks = DocumentChunker(
            make_document_indexing_policy(
                chunk_size=6,
                chunk_overlap=0,
            )
        ).chunk(make_document(body="  abc   def  "))

        self.assertEqual([chunk.text for chunk in chunks], ["abc", "def"])
        self.assertEqual(
            [(chunk.start_offset, chunk.end_offset) for chunk in chunks],
            [(0, 3), (6, 9)],
        )

    def test_document_chunk_ids_ignore_document_type(self) -> None:
        chunker = DocumentChunker(make_document_indexing_policy())

        document_chunk = chunker.chunk(make_document(document_type="document"))[0]
        note_chunk = chunker.chunk(make_document(document_type="note"))[0]

        self.assertEqual(document_chunk.chunk_id, note_chunk.chunk_id)

if __name__ == "__main__":
    unittest.main()
