from __future__ import annotations

import unittest
from contextlib import contextmanager

from foldmind_ai_core.core.application.commands.indexing import (
    DeleteDocumentIndexCommand,
    EvaluateFolderResponsibilityCommand,
    IndexDocumentCommand,
    UpdateDocumentFolderRelationsCommand,
)
from foldmind_ai_core.core.application.models.indexing import (
    DeletedDocumentIdentity,
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

    def upsert_document_index(
        self,
        *,
        document: SourceDocument,
        chunks: tuple[DocumentChunk, ...],
        profile: DocumentProfile,
        signals: tuple[DocumentSignal, ...],
    ) -> None:
        self.document_indexes.append(profile)
        self.document_chunks = list(chunks)
        self.document_signals = list(signals)
        self.operations.append("upsert_document_index")

    def replace_document_folder_relation_snapshot(
        self,
        *,
        snapshot: SourceDocumentFolderRelationSnapshot,
    ) -> bool:
        self.operations.append("replace_document_folder_relation_snapshot")
        return snapshot.document_id != "missing-doc"

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
        )

    def upsert_folder_index(
        self,
        *,
        folder: SourceFolder,
        signals: tuple[object, ...] = (),
    ) -> None:
        self.folder_indexes.append(folder)
        self.folder_signals = list(signals)
        self.operations.append("upsert_folder_index")

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
            signal_set_version="1",
        )
        signal = create_document_signal(
            tenant=document.tenant,
            document_type=document.document_type,
            document_id=document.document_id,
            source_version=document.source_version,
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
        )
        return FolderSignalExtraction(
            signals=(signal,),
            signal_set_version="folder-signals-v1",
            model="folder-model",
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
        self.assertEqual([event.event_type for event in uow.tx.events], ["DOCUMENT_DELETED"])
        self.assertEqual(uow.tx.events[0].source_id, "doc-1")
        self.assertEqual(uow.tx.events[0].tenant, "tenant-1")
        self.assertEqual(uow.tx.events[0].payload["affected_folder_ids"], ["folder-1"])
        self.assertEqual(
            uow.tx.operations,
            ["mark_document_deleted", "append_outbox"],
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
        self.assertEqual([event.event_type for event in uow.tx.events], ["DOCUMENT_DELETED"])
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
        self.assertEqual(uow.tx.folder_indexes[0].folder_id, "folder-1")
        self.assertEqual(uow.tx.folder_signals[0].metadata["signal_set_version"], "folder-signals-v1")
        self.assertEqual(uow.tx.folder_signals[0].metadata["model"], "folder-model")
        self.assertEqual([event.event_type for event in uow.tx.events], ["FOLDER_INDEXED"])
        self.assertEqual(uow.tx.events[0].payload["signals"][0]["text"], "Folder responsibility matches member documents.")
        self.assertEqual(
            uow.tx.operations,
            ["upsert_folder_index", "append_outbox"],
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
