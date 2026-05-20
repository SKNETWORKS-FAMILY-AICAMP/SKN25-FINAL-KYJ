from __future__ import annotations

import unittest
from contextlib import contextmanager

from foldmind_ai_core.core.application.commands.indexing import (
    DeleteDocumentIndexCommand,
    EvaluateFolderResponsibilityCommand,
    IndexDocumentCommand,
    IndexFolderCommand,
    UpdateDocumentFolderRelationsCommand,
)
from foldmind_ai_core.core.application.models.indexing import (
    DeletedDocumentIdentity,
    DocumentIndexChange,
    FolderIndexChange,
    FolderRelationChange,
    FolderSignalInvalidation,
    FolderSignalRefreshCommit,
    SourceDocumentFolderRelationSnapshot,
)
from foldmind_ai_core.core.domain.services.document_chunking import (
    DocumentChunker,
    DocumentChunkingConfig,
)
from foldmind_ai_core.core.application.use_cases.indexing.delete_document_index import (
    DeleteDocumentIndexUseCase,
)
from foldmind_ai_core.core.application.use_cases.indexing.evaluate_folder_responsibility import (
    EvaluateFolderResponsibilityUseCase,
)
from foldmind_ai_core.core.application.use_cases.indexing.index_document import IndexDocumentUseCase
from foldmind_ai_core.core.application.use_cases.indexing.index_folder import IndexFolderUseCase
from foldmind_ai_core.core.application.use_cases.indexing.update_document_folder_relations import (
    UpdateDocumentFolderRelationsUseCase,
)
from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.indexing.outbox import OutboxEvent
from foldmind_ai_core.core.domain.models.profiling import (
    DocumentProfile,
    DocumentSignal,
    DocumentSignalExtraction,
    DocumentSignalType,
    FolderSignalExtraction,
    FolderSignalType,
    SignalEvidence,
)
from foldmind_ai_core.core.domain.services.profiling import (
    create_document_signal,
    create_folder_signal,
)
from foldmind_ai_core.core.domain.models.reference.documents import SourceDocument
from foldmind_ai_core.core.domain.models.reference.folders import SourceFolder
from foldmind_ai_core.shared.validation import InvalidInputError

TEST_CHUNKING_VERSION = "chunking-test-v1"
TEST_EMBEDDING_MODEL = "embedding-test-model"
TEST_EMBEDDING_VERSION = "embedding-test-v1"
TEST_INDEX_SCHEMA_VERSION = "index-schema-test-v1"


class FakeIndexingTransaction:
    def __init__(self) -> None:
        self.document_indexes: list[DocumentProfile] = []
        self.document_chunks: list[DocumentChunk] = []
        self.document_signals: list[DocumentSignal] = []
        self.folder_indexes: list[SourceFolder] = []
        self.folder_signals: list[object] = []
        self.deleted_documents: list[str] = []
        self.events: list[OutboxEvent] = []
        self.operations: list[str] = []
        self.document_index_change = DocumentIndexChange(applied=True)
        self.folder_index_change = FolderIndexChange(applied=True)
        self.folder_relation_change = FolderRelationChange(applied=True)
        self.folder_signal_refresh_commit: FolderSignalRefreshCommit | None = None

    def upsert_document_index(
        self,
        *,
        document: SourceDocument,
        chunks: tuple[DocumentChunk, ...],
        profile: DocumentProfile,
        signals: tuple[DocumentSignal, ...],
    ) -> DocumentIndexChange:
        self.document_indexes.append(profile)
        self.document_chunks = list(chunks)
        self.document_signals = list(signals)
        self.operations.append("upsert_document_index")
        return self.document_index_change

    def replace_document_folder_relation_snapshot(
        self,
        *,
        snapshot: SourceDocumentFolderRelationSnapshot,
    ) -> FolderRelationChange:
        self.operations.append("replace_document_folder_relation_snapshot")
        if snapshot.document_id == "missing-doc":
            return FolderRelationChange(applied=False, source_exists=False)
        return self.folder_relation_change

    def mark_document_deleted(
        self,
        *,
        document_id: str,
    ) -> DeletedDocumentIdentity | None:
        self.deleted_documents.append(document_id)
        self.operations.append("mark_document_deleted")
        return DeletedDocumentIdentity(
            tenant="tenant-1",
            document_id=document_id,
            affected_folder_ids=("folder-1",),
            folder_signal_invalidations=(
                FolderSignalInvalidation(
                    tenant="tenant-1",
                    folder_id="folder-1",
                    index_input_digest="folder-signal-input-v1",
                ),
            ),
        )

    def upsert_folder_index(
        self,
        *,
        folder: SourceFolder,
    ) -> FolderIndexChange:
        self.folder_indexes.append(folder)
        self.operations.append("upsert_folder_index")
        return self.folder_index_change

    def current_folder_index_input_digest(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> str | None:
        self.operations.append("current_folder_index_input_digest")
        return "folder-signal-input-v1"

    def replace_folder_signals(
        self,
        *,
        folder: SourceFolder,
        signals: tuple[object, ...],
        expected_index_input_digest: str,
        signal_generation_version: str,
    ) -> FolderSignalRefreshCommit:
        self.folder_indexes.append(folder)
        self.operations.append("replace_folder_signals")
        commit = self.folder_signal_refresh_commit or FolderSignalRefreshCommit(
            applied=True,
            index_input_digest=expected_index_input_digest,
        )
        if commit.applied:
            self.folder_signals = list(signals)
        return commit

    def mark_folder_deleted(self, *, folder_id: str) -> object:
        raise AssertionError("document indexing tests should not delete folders")

    def append_outbox_event(self, event: OutboxEvent) -> None:
        self.events.append(event)
        self.operations.append("append_outbox")


class FakeIndexingUnitOfWork:
    def __init__(self) -> None:
        self.tx = FakeIndexingTransaction()
        self.opened = 0

    @contextmanager
    def transaction(self):
        self.opened += 1
        yield self.tx


class FakeDocumentProfiler:
    def profile(
        self,
        document: SourceDocument,
        chunks: list[DocumentChunk],
    ) -> DocumentSignalExtraction:
        profile = DocumentProfile(
            tenant=document.tenant,
            document_type=document.document_type,
            document_id=document.document_id,
            source_version=document.source_version,
            created_at=document.created_at,
            updated_at=document.updated_at,
            title=document.title or document.document_id,
            index_input_digest=chunks[0].index_input_digest,
        )
        signal = create_document_signal(
            tenant=document.tenant,
            document_type=document.document_type,
            document_id=document.document_id,
            source_version=document.source_version,
            index_input_digest=chunks[0].index_input_digest,
            signal_type=DocumentSignalType.SUMMARY,
            text="Document summary",
            attributes={},
            evidence=(
                SignalEvidence(
                    chunk_id=chunks[0].chunk_id,
                    quote=chunks[0].text,
                ),
            ),
            confidence=0.8,
            extractor_name="fake_profiler",
            extractor_version="test-v1",
            generation_model="fake-model",
        )
        return DocumentSignalExtraction(profile=profile, signals=(signal,))


class FakeFolderResponsibilitySourceRepository:
    def __init__(self, folder: SourceFolder | None = None) -> None:
        self.folder = folder

    def get_folder_source(self, *, tenant: str, folder_id: str) -> SourceFolder | None:
        return self.folder

    def list_member_document_sources(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> tuple[SourceDocument, ...]:
        return (make_document(),)


class FakeFolderSignalExtractor:
    def evaluate(
        self,
        folder: SourceFolder,
        member_documents: tuple[SourceDocument, ...],
    ) -> FolderSignalExtraction:
        signal = create_folder_signal(
            tenant=folder.tenant,
            folder_id=folder.folder_id,
            source_version=folder.source_version,
            signal_type=FolderSignalType.RESPONSIBILITY,
            signal_key="responsibility",
            text="Folder responsibility matches member documents.",
            attributes={"responsibility_score": 0.8},
            confidence=0.9,
            extractor_name="fake_folder_evaluator",
            extractor_version="test-v1",
            generation_model="folder-model",
            index_input_digest="pending-folder-signal-input",
        )
        return FolderSignalExtraction(
            signals=(signal,),
            signal_generation_version="folder-signals-v1",
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


def make_index_document_command(*, body: str = "body") -> IndexDocumentCommand:
    return IndexDocumentCommand(
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        source_version="v1",
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        title="",
        body=body,
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


def make_index_folder_command() -> IndexFolderCommand:
    return IndexFolderCommand(
        tenant="tenant-1",
        folder_id="folder-1",
        source_version="folder-v1",
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        name="Research",
        path="/Research",
        description="Research notes",
    )


def make_index_document_use_case(
    *,
    uow: FakeIndexingUnitOfWork | None = None,
    chunk_size: int = 1200,
    chunk_overlap: int = 120,
) -> IndexDocumentUseCase:
    return IndexDocumentUseCase(
        signal_extractor=FakeDocumentProfiler(),
        indexing_uow=uow or FakeIndexingUnitOfWork(),
        chunker=DocumentChunker(
            DocumentChunkingConfig(
                chunking_version=TEST_CHUNKING_VERSION,
                embedding_model=TEST_EMBEDDING_MODEL,
                embedding_version=TEST_EMBEDDING_VERSION,
                index_schema_version=TEST_INDEX_SCHEMA_VERSION,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        ),
    )


class IndexingUseCaseTests(unittest.TestCase):
    def test_empty_document_indexing_deletes_profile_and_publishes_outbox_event(self) -> None:
        uow = FakeIndexingUnitOfWork()

        result = make_index_document_use_case(
            uow=uow,
        ).execute(make_index_document_command(body=" "))

        self.assertEqual(result.indexed_chunk_count, 0)
        self.assertEqual(uow.tx.deleted_documents, ["doc-1"])
        self.assertEqual(
            [event.event_type for event in uow.tx.events],
            ["DOCUMENT_DELETED", "FOLDER_SIGNALS_INVALIDATED"],
        )
        self.assertEqual(uow.tx.events[0].source_id, "doc-1")
        self.assertEqual(uow.tx.events[0].tenant, "tenant-1")
        self.assertEqual(uow.tx.events[0].payload["affected_folder_ids"], ["folder-1"])
        self.assertEqual(
            uow.tx.operations,
            ["mark_document_deleted", "append_outbox", "append_outbox"],
        )

    def test_explicit_document_delete_deletes_profile_and_publishes_outbox_event(self) -> None:
        uow = FakeIndexingUnitOfWork()

        DeleteDocumentIndexUseCase(
            indexing_uow=uow,
        ).execute(
            DeleteDocumentIndexCommand(
                document_id="doc-1",
            )
        )

        self.assertEqual(uow.tx.deleted_documents, ["doc-1"])
        self.assertEqual(
            [event.event_type for event in uow.tx.events],
            ["DOCUMENT_DELETED", "FOLDER_SIGNALS_INVALIDATED"],
        )
        self.assertEqual(uow.tx.events[0].payload["affected_folder_ids"], ["folder-1"])
        self.assertEqual(
            uow.tx.events[0].partition_key,
            "document:tenant-1:doc-1",
        )

    def test_document_indexing_writes_profile_and_event_in_same_transaction(self) -> None:
        uow = FakeIndexingUnitOfWork()

        result = make_index_document_use_case(
            uow=uow,
        ).execute(make_index_document_command())

        self.assertEqual(result.indexed_chunk_count, 1)
        self.assertEqual(len(uow.tx.document_indexes), 1)
        self.assertEqual(len(uow.tx.document_chunks), 1)
        self.assertEqual([event.event_type for event in uow.tx.events], ["DOCUMENT_INDEXED"])
        self.assertEqual(uow.tx.events[0].payload["chunks"][0]["text"], "body")
        self.assertEqual(len(uow.tx.document_signals), 1)
        self.assertEqual(uow.tx.events[0].payload["signals"][0]["text"], "Document summary")
        self.assertEqual(
            uow.tx.operations,
            ["upsert_document_index", "append_outbox"],
        )

    def test_stale_document_indexing_does_not_publish_outbox_or_invalidate_folders(
        self,
    ) -> None:
        uow = FakeIndexingUnitOfWork()
        uow.tx.document_index_change = DocumentIndexChange(applied=False)

        result = make_index_document_use_case(
            uow=uow,
        ).execute(make_index_document_command())

        self.assertEqual(result.indexed_chunk_count, 0)
        self.assertEqual([event.event_type for event in uow.tx.events], [])
        self.assertEqual(uow.tx.operations, ["upsert_document_index"])

    def test_relation_change_invalidates_previous_and_current_folders(self) -> None:
        uow = FakeIndexingUnitOfWork()
        uow.tx.folder_relation_change = FolderRelationChange(
            applied=True,
            previous_folder_ids=("old-folder",),
            current_folder_ids=("new-folder",),
            folder_signal_invalidations=(
                FolderSignalInvalidation(
                    tenant="tenant-1",
                    folder_id="old-folder",
                    index_input_digest="old-folder-signal-input-v3",
                ),
                FolderSignalInvalidation(
                    tenant="tenant-1",
                    folder_id="new-folder",
                    index_input_digest="new-folder-signal-input-v1",
                ),
            ),
        )

        UpdateDocumentFolderRelationsUseCase(indexing_uow=uow).execute(
            UpdateDocumentFolderRelationsCommand(
                tenant="tenant-1",
                document_id="doc-1",
                source_version="v2",
                folder_ids=("new-folder",),
            )
        )

        self.assertEqual(
            [event.event_type for event in uow.tx.events],
            [
                "DOCUMENT_FOLDER_RELATIONS_INDEXED",
                "FOLDER_SIGNALS_INVALIDATED",
                "FOLDER_SIGNALS_INVALIDATED",
            ],
        )
        self.assertEqual(
            [event.source_id for event in uow.tx.events[1:]],
            ["old-folder", "new-folder"],
        )

    def test_stale_relation_change_does_not_publish_or_invalidate_folders(self) -> None:
        uow = FakeIndexingUnitOfWork()
        uow.tx.folder_relation_change = FolderRelationChange(
            applied=False,
            previous_folder_ids=("old-folder",),
            current_folder_ids=("old-folder",),
        )

        UpdateDocumentFolderRelationsUseCase(indexing_uow=uow).execute(
            UpdateDocumentFolderRelationsCommand(
                tenant="tenant-1",
                document_id="doc-1",
                source_version="v1",
                folder_ids=("new-folder",),
            )
        )

        self.assertEqual(uow.tx.events, [])
        self.assertEqual(
            uow.tx.operations,
            ["replace_document_folder_relation_snapshot"],
        )

    def test_folder_source_indexing_splits_source_and_signal_invalidation_events(
        self,
    ) -> None:
        uow = FakeIndexingUnitOfWork()
        uow.tx.folder_index_change = FolderIndexChange(
            applied=True,
            folder_signal_invalidation=FolderSignalInvalidation(
                tenant="tenant-1",
                folder_id="folder-1",
                index_input_digest="folder-signal-input-v2",
            ),
        )

        result = IndexFolderUseCase(indexing_uow=uow).execute(make_index_folder_command())

        self.assertEqual(result.folder_id, "folder-1")
        self.assertEqual(
            [event.event_type for event in uow.tx.events],
            ["FOLDER_INDEXED", "FOLDER_SIGNALS_INVALIDATED"],
        )
        self.assertNotIn("signals", uow.tx.events[0].payload)
        self.assertEqual(
            uow.tx.events[1].payload,
            {
                "tenant": "tenant-1",
                "folder_id": "folder-1",
                "index_input_digest": "folder-signal-input-v2",
                "signal_generation_version": "1",
            },
        )

    def test_document_chunker_validates_config_and_preserves_offsets(self) -> None:
        chunks = DocumentChunker(
            DocumentChunkingConfig(
                chunking_version=TEST_CHUNKING_VERSION,
                embedding_model=TEST_EMBEDDING_MODEL,
                embedding_version=TEST_EMBEDDING_VERSION,
                index_schema_version=TEST_INDEX_SCHEMA_VERSION,
                chunk_size=4,
                chunk_overlap=1,
            )
        ).chunk(make_document(body="abcdefg"))

        self.assertEqual([chunk.text for chunk in chunks], ["abcd", "defg", "g"])
        self.assertTrue(all(chunk.text_hash for chunk in chunks))
        self.assertEqual(chunks[0].embedding_model, TEST_EMBEDDING_MODEL)
        self.assertEqual(chunks[0].embedding_version, TEST_EMBEDDING_VERSION)
        self.assertEqual(chunks[0].index_schema_version, TEST_INDEX_SCHEMA_VERSION)
        self.assertTrue(chunks[0].index_input_digest)
        self.assertEqual(
            [(chunk.start_offset, chunk.end_offset) for chunk in chunks],
            [(0, 4), (3, 7), (6, 7)],
        )
        with self.assertRaises(InvalidInputError):
            DocumentChunkingConfig(
                chunking_version=TEST_CHUNKING_VERSION,
                embedding_model=TEST_EMBEDDING_MODEL,
                embedding_version=TEST_EMBEDDING_VERSION,
                index_schema_version=TEST_INDEX_SCHEMA_VERSION,
                chunk_size=4,
                chunk_overlap=4,
            )
        with self.assertRaises(InvalidInputError):
            DocumentChunkingConfig(
                chunking_version=TEST_CHUNKING_VERSION,
                embedding_model=TEST_EMBEDDING_MODEL,
                embedding_version=TEST_EMBEDDING_VERSION,
                index_schema_version=TEST_INDEX_SCHEMA_VERSION,
                chunk_size=True,
                chunk_overlap=0,
            )
        with self.assertRaises(InvalidInputError):
            DocumentChunkingConfig(
                chunking_version=TEST_CHUNKING_VERSION,
                embedding_model=TEST_EMBEDDING_MODEL,
                embedding_version=TEST_EMBEDDING_VERSION,
                index_schema_version=TEST_INDEX_SCHEMA_VERSION,
                chunk_size=4,
                chunk_overlap=False,
            )

    def test_document_chunker_offsets_match_trimmed_chunk_text(self) -> None:
        chunks = DocumentChunker(
            DocumentChunkingConfig(
                chunking_version=TEST_CHUNKING_VERSION,
                embedding_model=TEST_EMBEDDING_MODEL,
                embedding_version=TEST_EMBEDDING_VERSION,
                index_schema_version=TEST_INDEX_SCHEMA_VERSION,
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
        chunker = DocumentChunker(
            DocumentChunkingConfig(
                chunking_version=TEST_CHUNKING_VERSION,
                embedding_model=TEST_EMBEDDING_MODEL,
                embedding_version=TEST_EMBEDDING_VERSION,
                index_schema_version=TEST_INDEX_SCHEMA_VERSION,
                chunk_size=1200,
                chunk_overlap=120,
            )
        )

        document_chunk = chunker.chunk(make_document(document_type="document"))[0]
        note_chunk = chunker.chunk(make_document(document_type="note"))[0]

        self.assertEqual(document_chunk.chunk_id, note_chunk.chunk_id)

    def test_folder_responsibility_evaluation_stores_folder_signals_and_event(self) -> None:
        uow = FakeIndexingUnitOfWork()

        result = EvaluateFolderResponsibilityUseCase(
            source_repository=FakeFolderResponsibilitySourceRepository(make_folder()),
            signal_extractor=FakeFolderSignalExtractor(),
            indexing_uow=uow,
        ).execute(
            EvaluateFolderResponsibilityCommand(
                tenant="tenant-1",
                folder_id="folder-1",
            )
        )

        self.assertEqual(result.signal_count, 1)
        self.assertEqual(uow.tx.folder_signals[0].generation_model, "folder-model")
        self.assertEqual(uow.tx.folder_signals[0].index_input_digest, "folder-signal-input-v1")
        self.assertEqual([event.event_type for event in uow.tx.events], ["FOLDER_SIGNALS_INDEXED"])
        self.assertEqual(uow.tx.events[0].payload["signals"][0]["text"], "Folder responsibility matches member documents.")
        self.assertEqual(
            uow.tx.operations,
            ["current_folder_index_input_digest", "replace_folder_signals", "append_outbox"],
        )

    def test_folder_responsibility_evaluation_discards_raced_revision(self) -> None:
        uow = FakeIndexingUnitOfWork()
        uow.tx.folder_signal_refresh_commit = FolderSignalRefreshCommit(
            applied=False,
            index_input_digest="folder-signal-input-v1",
        )

        result = EvaluateFolderResponsibilityUseCase(
            source_repository=FakeFolderResponsibilitySourceRepository(make_folder()),
            signal_extractor=FakeFolderSignalExtractor(),
            indexing_uow=uow,
        ).execute(
            EvaluateFolderResponsibilityCommand(
                tenant="tenant-1",
                folder_id="folder-1",
            )
        )

        self.assertEqual(result.signal_count, 0)
        self.assertEqual(uow.tx.folder_signals, [])
        self.assertEqual(uow.tx.events, [])
        self.assertEqual(
            uow.tx.operations,
            ["current_folder_index_input_digest", "replace_folder_signals"],
        )

    def test_folder_responsibility_evaluation_requires_existing_folder(self) -> None:
        with self.assertRaisesRegex(Exception, "Folder source not found"):
            EvaluateFolderResponsibilityUseCase(
                source_repository=FakeFolderResponsibilitySourceRepository(None),
                signal_extractor=FakeFolderSignalExtractor(),
                indexing_uow=FakeIndexingUnitOfWork(),
            ).execute(
                EvaluateFolderResponsibilityCommand(
                    tenant="tenant-1",
                    folder_id="missing-folder",
                )
            )


if __name__ == "__main__":
    unittest.main()
