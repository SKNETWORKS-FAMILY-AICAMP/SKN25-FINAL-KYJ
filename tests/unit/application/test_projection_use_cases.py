from __future__ import annotations

import unittest
from dataclasses import replace

from foldmind_ai_core.core.application.errors import ProviderContractError
from foldmind_ai_core.core.application.commands.projection import (
    DeleteDocumentProjectionCommand,
    DeleteFolderProjectionCommand,
    ProjectDocumentFolderRelationsCommand,
    ProjectDocumentCommand,
    ProjectFolderCommand,
)
from foldmind_ai_core.core.application.models.projection_inputs import (
    ProjectionDocument,
    ProjectionDocumentFolderRelationSnapshot,
    ProjectionDocumentProfile,
    ProjectionDocumentSignal,
    ProjectionFolder,
    ProjectionFolderSignal,
    ProjectionSignalEvidence,
)
from foldmind_ai_core.core.application.ports.outbound.vector_store import VectorWriteResult
from foldmind_ai_core.core.application.projections.graph import (
    DocumentRelationshipProjection,
    DocumentSignalProjection,
    FolderRelationshipProjection,
    FolderSignalProjection,
)
from foldmind_ai_core.core.application.projections.vector import (
    DocumentChunkVectorProjection,
    DocumentSignalVectorProjection,
    DocumentVectorProjection,
    FolderSignalVectorProjection,
    FolderVectorProjection,
)
from foldmind_ai_core.core.application.queries.retrieval import SearchScope
from foldmind_ai_core.core.application.services.vector_projection_spec import VectorProjectionSpec
from foldmind_ai_core.core.application.use_cases.projection.document_chunk_vector_projection import (
    DeleteDocumentChunkVectorsUseCase,
    ProjectDocumentChunkVectorsUseCase,
)
from foldmind_ai_core.core.application.use_cases.projection.document_vector_projection import (
    DeleteDocumentSignalVectorsUseCase,
    DeleteDocumentVectorUseCase,
    ProjectDocumentSignalVectorsUseCase,
    ProjectDocumentVectorUseCase,
)
from foldmind_ai_core.core.application.use_cases.projection.folder_vector_projection import (
    DeleteFolderSignalVectorsUseCase,
    DeleteFolderVectorUseCase,
    ProjectFolderSignalVectorsUseCase,
    ProjectFolderVectorUseCase,
)
from foldmind_ai_core.core.application.use_cases.projection.graph_projection import (
    DeleteDocumentGraphUseCase,
    DeleteFolderGraphUseCase,
    ProjectDocumentFolderRelationsGraphUseCase,
    ProjectDocumentGraphUseCase,
    ProjectFolderGraphUseCase,
)
from foldmind_ai_core.core.domain.models.retrieval.results import (
    DocumentRetrievalResult,
    FolderRetrievalResult,
    RetrievalResult,
    RetrievedFolder,
    SignalRetrievalResult,
)
from foldmind_ai_core.shared.types import Vector
from foldmind_ai_core.shared.validation import InvalidInputError

TEST_EMBEDDING_MODEL = "embedding-test-model"
TEST_EMBEDDING_VERSION = "embedding-test-v1"
TEST_INDEX_SCHEMA_VERSION = "index-schema-test-v1"


class FakeEmbeddingProvider:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def embed_texts(self, texts: list[str]) -> list[Vector]:
        self.texts.extend(texts)
        return [[float(len(text))] for text in texts]


class ShortEmbeddingProvider:
    def embed_texts(self, texts: list[str]) -> list[Vector]:
        return []


class FakeSourceFreshnessChecker:
    def __init__(self, *, folder_current: bool = True) -> None:
        self.folder_current = folder_current
        self.folder_calls: list[tuple[str, str, str]] = []
        self.document_folder_relation_calls: list[tuple[str, str, str]] = []

    def is_current_document_source(
        self,
        *,
        tenant: str,
        document_id: str,
        source_version: str,
        content_digest: str,
    ) -> bool:
        return True

    def is_current_folder_source(
        self,
        *,
        tenant: str,
        folder_id: str,
        source_version: str,
    ) -> bool:
        self.folder_calls.append((tenant, folder_id, source_version))
        return self.folder_current

    def is_current_document_folder_relation_snapshot(
        self,
        *,
        tenant: str,
        document_id: str,
        source_version: str,
    ) -> bool:
        self.document_folder_relation_calls.append(
            (tenant, document_id, source_version)
        )
        return self.folder_current


class FakeDocumentChunkVectorStore:
    def __init__(self) -> None:
        self.chunks_by_document: dict[str, tuple[str, ...]] = {}
        self.deleted: list[str] = []

    def replace_document_chunks(
        self,
        *,
        tenant: str,
        document_id: str,
        chunks: tuple[object, ...],
        vectors: tuple[Vector, ...],
    ) -> tuple[VectorWriteResult, ...]:
        self.chunks_by_document[document_id] = tuple(chunk.chunk_id for chunk in chunks)
        return tuple(
            VectorWriteResult(
                collection_name="chunks",
                point_id=str(chunk.chunk_id),
                payload_digest=f"chunk:{chunk.chunk_id}",
            )
            for chunk in chunks
        )

    def delete_document_chunks(
        self,
        *,
        document_id: str,
    ) -> None:
        self.deleted.append(document_id)
        self.chunks_by_document.pop(document_id, None)

    def search_chunks(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[RetrievalResult]:
        return []


class FakeDocumentVectorStore:
    def __init__(self) -> None:
        self.documents: dict[str, str] = {}
        self.deleted: list[str] = []

    def upsert_document_vector(
        self,
        *,
        projection: DocumentVectorProjection,
        vector: Vector,
    ) -> VectorWriteResult:
        self.documents[projection.document_id] = projection.embedding_input
        return VectorWriteResult(
            collection_name="documents",
            point_id=projection.document_id,
            payload_digest=f"document:{projection.document_id}",
        )

    def delete_document_vector(
        self,
        *,
        document_id: str,
    ) -> None:
        self.deleted.append(document_id)
        self.documents.pop(document_id, None)

    def search_documents(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[DocumentRetrievalResult]:
        return []


class FakeSignalVectorStore:
    def __init__(self) -> None:
        self.signals_by_document: dict[str, tuple[str, ...]] = {}
        self.signals_by_folder: dict[str, tuple[str, ...]] = {}
        self.deleted_documents: list[str] = []
        self.deleted_folders: list[str] = []

    def replace_document_signals(
        self,
        *,
        tenant: str,
        document_id: str,
        signals: tuple[DocumentSignalVectorProjection, ...],
        vectors: tuple[Vector, ...],
    ) -> tuple[VectorWriteResult, ...]:
        self.signals_by_document[document_id] = tuple(
            signal.signal_id for signal in signals
        )
        return tuple(
            VectorWriteResult(
                collection_name="signals",
                point_id=signal.signal_id,
                payload_digest=f"signal:{signal.signal_id}",
            )
            for signal in signals
        )

    def delete_document_signals(
        self,
        *,
        document_id: str,
    ) -> None:
        self.deleted_documents.append(document_id)
        self.signals_by_document.pop(document_id, None)

    def replace_folder_signals(
        self,
        *,
        tenant: str,
        folder_id: str,
        signals: tuple[FolderSignalVectorProjection, ...],
        vectors: tuple[Vector, ...],
    ) -> tuple[VectorWriteResult, ...]:
        self.delete_folder_signals(folder_id=folder_id)
        if signals:
            self.signals_by_folder[folder_id] = tuple(
                signal.signal_id for signal in signals
            )
        else:
            self.signals_by_folder.pop(folder_id, None)
        return tuple(
            VectorWriteResult(
                collection_name="signals",
                point_id=f"folder:{signal.signal_id}",
                payload_digest=f"folder-signal:{signal.signal_id}",
            )
            for signal in signals
        )

    def delete_folder_signals(
        self,
        *,
        folder_id: str,
    ) -> None:
        self.deleted_folders.append(folder_id)
        self.signals_by_folder.pop(folder_id, None)

    def search_signals(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        signal_type: str | None = None,
        scope: SearchScope | None = None,
    ) -> list[SignalRetrievalResult]:
        return []


class FakeFolderVectorStore:
    def __init__(self) -> None:
        self.folders: dict[str, str] = {}
        self.deleted: list[str] = []

    def upsert_folder_vector(
        self,
        *,
        projection: FolderVectorProjection,
        vector: Vector,
    ) -> VectorWriteResult:
        self.folders[projection.folder_id] = projection.source_version
        return VectorWriteResult(
            collection_name="folders",
            point_id=projection.folder_id,
            payload_digest=f"folder:{projection.folder_id}",
        )

    def delete_folder_vector(self, *, folder_id: str) -> None:
        self.deleted.append(folder_id)
        self.folders.pop(folder_id, None)

    def search_folders(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[FolderRetrievalResult]:
        return []


class FakeGraphStore:
    def __init__(self) -> None:
        self.relationships: dict[str, tuple[str, ...]] = {}
        self.signals: dict[str, tuple[str, ...]] = {}
        self.folders: dict[str, str | None] = {}
        self.deleted_documents: list[str] = []
        self.deleted_folder_signals: list[str] = []
        self.deleted_folders: list[str] = []

    def replace_document_projection(
        self,
        *,
        relationships: DocumentRelationshipProjection,
        signals: DocumentSignalProjection,
    ) -> None:
        self.relationships[relationships.document_id] = ()
        self.signals[signals.document_id] = tuple(
            signal.signal_id for signal in signals.signals
        )

    def replace_document_folder_relations(
        self,
        *,
        projection,
    ) -> None:
        self.relationships[projection.document_id] = projection.folder_ids

    def replace_folder_projection(
        self,
        *,
        relationships: FolderRelationshipProjection,
        signals: FolderSignalProjection,
    ) -> None:
        self.folders[relationships.folder_id] = relationships.parent_folder_id

    def document_ids_for_scope(
        self,
        *,
        tenant: str,
        scope: SearchScope,
    ) -> tuple[str, ...]:
        return ()

    def folders_for_documents(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
    ) -> dict[str, tuple[RetrievedFolder, ...]]:
        return {}

    def delete_document(
        self,
        *,
        document_id: str,
    ) -> None:
        self.deleted_documents.append(document_id)
        self.relationships.pop(document_id, None)
        self.signals.pop(document_id, None)

    def delete_folder_signals(self, *, folder_id: str) -> None:
        self.deleted_folder_signals.append(folder_id)

    def delete_folder(self, *, folder_id: str) -> None:
        self.deleted_folders.append(folder_id)
        self.folders.pop(folder_id, None)

    def graph_search(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[DocumentRetrievalResult]:
        return []


class FakeProjectionLedger:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def record_document_vector_projected(
        self,
        *,
        projection: DocumentVectorProjection,
        write: VectorWriteResult,
    ) -> None:
        self.calls.append(("document_vector", projection.document_id, write.point_id))

    def record_chunk_vectors_projected(
        self,
        *,
        projections: tuple[DocumentChunkVectorProjection, ...],
        writes: tuple[VectorWriteResult, ...],
    ) -> None:
        self.calls.extend(
            ("chunk_vector", projection.chunk_id, write.point_id)
            for projection, write in zip(projections, writes, strict=True)
        )

    def record_signal_vectors_projected(
        self,
        *,
        projections: tuple[DocumentSignalVectorProjection, ...],
        writes: tuple[VectorWriteResult, ...],
    ) -> None:
        self.calls.extend(
            ("signal_vector", projection.signal_id, write.point_id)
            for projection, write in zip(projections, writes, strict=True)
        )

    def record_folder_signal_vectors_projected(
        self,
        *,
        projections: tuple[FolderSignalVectorProjection, ...],
        writes: tuple[VectorWriteResult, ...],
    ) -> None:
        self.calls.extend(
            ("folder_signal_vector", projection.signal_id, write.point_id)
            for projection, write in zip(projections, writes, strict=True)
        )

    def record_folder_vector_projected(
        self,
        *,
        projection: FolderVectorProjection,
        write: VectorWriteResult,
    ) -> None:
        self.calls.append(("folder_vector", projection.folder_id, write.point_id))

    def delete_document_vector_records(
        self,
        *,
        document_id: str,
    ) -> None:
        self.calls.append(("document_vector_deleted", document_id))

    def delete_chunk_vector_records(
        self,
        *,
        document_id: str,
    ) -> None:
        self.calls.append(("chunk_vectors_deleted", document_id))

    def delete_signal_vector_records(
        self,
        *,
        document_id: str,
    ) -> None:
        self.calls.append(("signal_vectors_deleted", document_id))

    def delete_folder_signal_vector_records(self, *, folder_id: str) -> None:
        self.calls.append(("folder_signal_vectors_deleted", folder_id))

    def delete_folder_vector_records(self, *, folder_id: str) -> None:
        self.calls.append(("folder_vectors_deleted", folder_id))


class ProjectionUseCaseTests(unittest.TestCase):
    def test_vector_projection_spec_rejects_blank_projection_metadata(self) -> None:
        with self.assertRaises(InvalidInputError):
            VectorProjectionSpec(
                embedding_model=" ",
                embedding_version=TEST_EMBEDDING_VERSION,
                index_schema_version=TEST_INDEX_SCHEMA_VERSION,
            )

        with self.assertRaises(InvalidInputError):
            VectorProjectionSpec(
                embedding_model=TEST_EMBEDDING_MODEL,
                embedding_version=" ",
                index_schema_version=TEST_INDEX_SCHEMA_VERSION,
            )

        with self.assertRaises(InvalidInputError):
            VectorProjectionSpec(
                embedding_model=TEST_EMBEDDING_MODEL,
                embedding_version=TEST_EMBEDDING_VERSION,
                index_schema_version=" ",
            )

    def test_project_document_command_projects_each_target_independently(self) -> None:
        embeddings = FakeEmbeddingProvider()
        chunk_vectors = FakeDocumentChunkVectorStore()
        document_vectors = FakeDocumentVectorStore()
        signal_vectors = FakeSignalVectorStore()
        graph = FakeGraphStore()
        ledger = FakeProjectionLedger()
        command = _project_document_command()
        projection_spec = VectorProjectionSpec(
            embedding_model=TEST_EMBEDDING_MODEL,
            embedding_version=TEST_EMBEDDING_VERSION,
            index_schema_version=TEST_INDEX_SCHEMA_VERSION,
        )

        chunk_projection = ProjectDocumentChunkVectorsUseCase(
            embeddings=embeddings,
            chunk_vectors=chunk_vectors,
            projection_ledger=ledger,
        )
        document_projection = ProjectDocumentVectorUseCase(
            embeddings=embeddings,
            document_vectors=document_vectors,
            projection_spec=projection_spec,
            projection_ledger=ledger,
        )
        signal_projection = ProjectDocumentSignalVectorsUseCase(
            embeddings=embeddings,
            signal_vectors=signal_vectors,
            projection_spec=projection_spec,
            projection_ledger=ledger,
        )
        graph_projection = ProjectDocumentGraphUseCase(
            graph=graph,
        )

        for _ in range(5):
            chunk_projection.execute(command)
            document_projection.execute(command)
            signal_projection.execute(command)
            graph_projection.execute(command)

        self.assertEqual(chunk_vectors.chunks_by_document, {"doc-1": ("chunk-1",)})
        self.assertIn("Summary", document_vectors.documents["doc-1"])
        self.assertEqual(signal_vectors.signals_by_document["doc-1"], ("signal-1",))
        self.assertEqual(graph.relationships["doc-1"], ())
        self.assertEqual(graph.signals["doc-1"], ("signal-1",))
        self.assertEqual(embeddings.texts.count("chunk text"), 5)
        self.assertEqual(embeddings.texts.count("Title\n\nSummary"), 5)
        self.assertEqual(embeddings.texts.count("Summary"), 5)
        self.assertEqual(
            ledger.calls.count(("chunk_vector", "chunk-1", "chunk-1")),
            5,
        )
        self.assertEqual(
            ledger.calls.count(("document_vector", "doc-1", "doc-1")),
            5,
        )
        self.assertEqual(
            ledger.calls.count(("signal_vector", "signal-1", "signal-1")),
            5,
        )

    def test_empty_chunk_projection_skips_embedding_call(self) -> None:
        embeddings = FakeEmbeddingProvider()
        chunk_vectors = FakeDocumentChunkVectorStore()
        ledger = FakeProjectionLedger()

        ProjectDocumentChunkVectorsUseCase(
            embeddings=embeddings,
            chunk_vectors=chunk_vectors,
            projection_ledger=ledger,
        ).execute(replace(_project_document_command(), chunks=()))

        self.assertEqual(embeddings.texts, [])
        self.assertEqual(chunk_vectors.chunks_by_document, {"doc-1": ()})
        self.assertEqual(ledger.calls, [("chunk_vectors_deleted", "doc-1")])

    def test_vector_projection_rejects_embedding_count_mismatch(self) -> None:
        command = _project_document_command()
        projection_spec = VectorProjectionSpec(
            embedding_model=TEST_EMBEDDING_MODEL,
            embedding_version=TEST_EMBEDDING_VERSION,
            index_schema_version=TEST_INDEX_SCHEMA_VERSION,
        )

        with self.assertRaises(ProviderContractError):
            ProjectDocumentChunkVectorsUseCase(
                embeddings=ShortEmbeddingProvider(),
                chunk_vectors=FakeDocumentChunkVectorStore(),
            ).execute(command)

        with self.assertRaises(ProviderContractError):
            ProjectDocumentVectorUseCase(
                embeddings=ShortEmbeddingProvider(),
                document_vectors=FakeDocumentVectorStore(),
                projection_spec=projection_spec,
            ).execute(command)

        with self.assertRaises(ProviderContractError):
            ProjectDocumentSignalVectorsUseCase(
                embeddings=ShortEmbeddingProvider(),
                signal_vectors=FakeSignalVectorStore(),
                projection_spec=projection_spec,
            ).execute(command)

        with self.assertRaises(ProviderContractError):
            ProjectFolderVectorUseCase(
                embeddings=ShortEmbeddingProvider(),
                folder_vectors=FakeFolderVectorStore(),
                projection_spec=projection_spec,
            ).execute(
                ProjectFolderCommand(
                    folder=ProjectionFolder(
                        tenant="tenant-1",
                        folder_id="folder-1",
                        source_version="folder-v1",
                        created_at="2026-05-01T10:00:00+09:00",
                        updated_at="2026-05-02T11:00:00+09:00",
                        name="Startup",
                    )
                )
            )

    def test_delete_events_project_each_target_independently(self) -> None:
        chunk_vectors = FakeDocumentChunkVectorStore()
        document_vectors = FakeDocumentVectorStore()
        signal_vectors = FakeSignalVectorStore()
        folder_vectors = FakeFolderVectorStore()
        graph = FakeGraphStore()
        ledger = FakeProjectionLedger()
        document_command = DeleteDocumentProjectionCommand(
            document_id="doc-1",
            affected_folder_ids=("folder-1", "folder-2"),
        )
        folder_command = DeleteFolderProjectionCommand(
            folder_id="folder-1",
        )

        for _ in range(2):
            DeleteDocumentChunkVectorsUseCase(
                chunk_vectors=chunk_vectors,
                projection_ledger=ledger,
            ).execute(document_command)
            DeleteDocumentVectorUseCase(
                document_vectors=document_vectors,
                projection_ledger=ledger,
            ).execute(document_command)
            DeleteDocumentSignalVectorsUseCase(
                signal_vectors=signal_vectors,
                projection_ledger=ledger,
            ).execute(document_command)
            DeleteDocumentGraphUseCase(
                graph=graph,
            ).execute(document_command)
            DeleteFolderVectorUseCase(
                folder_vectors=folder_vectors,
                projection_ledger=ledger,
            ).execute(folder_command)
            DeleteFolderSignalVectorsUseCase(
                signal_vectors=signal_vectors,
                projection_ledger=ledger,
            ).execute(folder_command)
            DeleteFolderGraphUseCase(
                graph=graph,
            ).execute(folder_command)

        self.assertEqual(chunk_vectors.deleted, ["doc-1", "doc-1"])
        self.assertEqual(document_vectors.deleted, ["doc-1", "doc-1"])
        self.assertEqual(signal_vectors.deleted_documents, ["doc-1", "doc-1"])
        self.assertEqual(
            signal_vectors.deleted_folders,
            ["folder-1", "folder-2", "folder-1", "folder-1", "folder-2", "folder-1"],
        )
        self.assertEqual(graph.deleted_documents, ["doc-1", "doc-1"])
        self.assertEqual(
            graph.deleted_folder_signals,
            ["folder-1", "folder-2", "folder-1", "folder-2"],
        )
        self.assertEqual(folder_vectors.deleted, ["folder-1", "folder-1"])
        self.assertEqual(graph.deleted_folders, ["folder-1", "folder-1"])
        self.assertEqual(
            ledger.calls.count(("chunk_vectors_deleted", "doc-1")),
            2,
        )
        self.assertEqual(
            ledger.calls.count(("document_vector_deleted", "doc-1")),
            2,
        )
        self.assertEqual(
            ledger.calls.count(("signal_vectors_deleted", "doc-1")),
            2,
        )
        self.assertEqual(
            ledger.calls.count(("folder_signal_vectors_deleted", "folder-2")),
            2,
        )
        self.assertEqual(
            ledger.calls.count(("folder_vectors_deleted", "folder-1")),
            2,
        )
        self.assertEqual(
            ledger.calls.count(("folder_signal_vectors_deleted", "folder-1")),
            4,
        )

    def test_project_folder_command_projects_each_target_independently(self) -> None:
        embeddings = FakeEmbeddingProvider()
        signal_vectors = FakeSignalVectorStore()
        folder_vectors = FakeFolderVectorStore()
        graph = FakeGraphStore()
        ledger = FakeProjectionLedger()
        command = ProjectFolderCommand(
            folder=ProjectionFolder(
                tenant="tenant-1",
                folder_id="folder-1",
                source_version="folder-v1",
                created_at="2026-05-01T10:00:00+09:00",
                updated_at="2026-05-02T11:00:00+09:00",
                name="Startup",
                parent_folder_id="root",
            ),
            signals=(
                ProjectionFolderSignal(
                    signal_id="folder-signal-1",
                    tenant="tenant-1",
                    folder_id="folder-1",
                    source_version="folder-v1",
                    signal_type="responsibility",
                    signal_key="responsibility",
                    text="Startup folder responsibility.",
                ),
            ),
        )

        ProjectFolderVectorUseCase(
            embeddings=embeddings,
            folder_vectors=folder_vectors,
            projection_ledger=ledger,
            projection_spec=VectorProjectionSpec(
                embedding_model=TEST_EMBEDDING_MODEL,
                embedding_version=TEST_EMBEDDING_VERSION,
                index_schema_version=TEST_INDEX_SCHEMA_VERSION,
            ),
        ).execute(command)
        ProjectFolderSignalVectorsUseCase(
            embeddings=embeddings,
            signal_vectors=signal_vectors,
            projection_ledger=ledger,
            projection_spec=VectorProjectionSpec(
                embedding_model=TEST_EMBEDDING_MODEL,
                embedding_version=TEST_EMBEDDING_VERSION,
                index_schema_version=TEST_INDEX_SCHEMA_VERSION,
            ),
        ).execute(command)
        ProjectFolderGraphUseCase(
            graph=graph,
        ).execute(command)

        self.assertEqual(folder_vectors.folders, {"folder-1": "folder-v1"})
        self.assertEqual(
            signal_vectors.signals_by_folder,
            {"folder-1": ("folder-signal-1",)},
        )
        self.assertEqual(graph.folders, {"folder-1": "root"})
        self.assertEqual(
            embeddings.texts,
            [
                "Startup\n\nStartup folder responsibility.",
                "Startup folder responsibility.",
            ],
        )
        self.assertIn(("folder_vector", "folder-1", "folder-1"), ledger.calls)
        self.assertIn(
            ("folder_signal_vector", "folder-signal-1", "folder:folder-signal-1"),
            ledger.calls,
        )

    def test_folder_signal_projection_skips_stale_source(self) -> None:
        embeddings = FakeEmbeddingProvider()
        signal_vectors = FakeSignalVectorStore()
        ledger = FakeProjectionLedger()
        source_freshness = FakeSourceFreshnessChecker(folder_current=False)
        command = _project_folder_command()

        ProjectFolderSignalVectorsUseCase(
            embeddings=embeddings,
            signal_vectors=signal_vectors,
            projection_ledger=ledger,
            source_freshness=source_freshness,
            projection_spec=VectorProjectionSpec(
                embedding_model=TEST_EMBEDDING_MODEL,
                embedding_version=TEST_EMBEDDING_VERSION,
                index_schema_version=TEST_INDEX_SCHEMA_VERSION,
            ),
        ).execute(command)

        self.assertEqual(embeddings.texts, [])
        self.assertEqual(signal_vectors.signals_by_folder, {})
        self.assertEqual(signal_vectors.deleted_folders, [])
        self.assertEqual(ledger.calls, [])
        self.assertEqual(
            source_freshness.folder_calls,
            [("tenant-1", "folder-1", "folder-v1")],
        )

    def test_document_folder_relation_graph_projection_replaces_edges(self) -> None:
        graph = FakeGraphStore()
        source_freshness = FakeSourceFreshnessChecker()
        command = ProjectDocumentFolderRelationsCommand(
            folder_relation_snapshot=ProjectionDocumentFolderRelationSnapshot(
                tenant="tenant-1",
                document_id="doc-1",
                source_version="rel-v1",
                folder_ids=("folder-1",),
            )
        )

        ProjectDocumentFolderRelationsGraphUseCase(
            graph=graph,
            source_freshness=source_freshness,
        ).execute(command)

        self.assertEqual(graph.relationships["doc-1"], ("folder-1",))
        self.assertEqual(
            source_freshness.document_folder_relation_calls,
            [("tenant-1", "doc-1", "rel-v1")],
        )

    def test_empty_folder_signal_projection_deletes_previous_vectors(self) -> None:
        embeddings = FakeEmbeddingProvider()
        signal_vectors = FakeSignalVectorStore()
        signal_vectors.signals_by_folder["folder-1"] = ("old-signal",)
        ledger = FakeProjectionLedger()

        ProjectFolderSignalVectorsUseCase(
            embeddings=embeddings,
            signal_vectors=signal_vectors,
            projection_ledger=ledger,
            projection_spec=VectorProjectionSpec(
                embedding_model=TEST_EMBEDDING_MODEL,
                embedding_version=TEST_EMBEDDING_VERSION,
                index_schema_version=TEST_INDEX_SCHEMA_VERSION,
            ),
        ).execute(replace(_project_folder_command(), signals=()))

        self.assertEqual(embeddings.texts, [])
        self.assertEqual(signal_vectors.signals_by_folder, {})
        self.assertEqual(signal_vectors.deleted_folders, ["folder-1"])
        self.assertEqual(ledger.calls, [("folder_signal_vectors_deleted", "folder-1")])


def _project_document_command() -> ProjectDocumentCommand:
    document = ProjectionDocument(
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        source_version="v1",
        content_digest="content-digest-1",
        content_size_bytes=12,
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        title="Title",
    )
    chunk = DocumentChunkVectorProjection(
        tenant=document.tenant,
        document_type=document.document_type,
        document_id=document.document_id,
        source_version=document.source_version,
        content_digest=document.content_digest,
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
        embedding_version="v1",
        index_schema_version="schema-v1",
    )
    profile = ProjectionDocumentProfile(
        tenant=document.tenant,
        document_type=document.document_type,
        document_id=document.document_id,
        source_version=document.source_version,
        content_digest=document.content_digest,
        created_at=document.created_at,
        updated_at=document.updated_at,
        title=document.title,
        signal_set_version="1",
    )
    signal = ProjectionDocumentSignal(
        signal_id="signal-1",
        tenant=document.tenant,
        document_type=document.document_type,
        document_id=document.document_id,
        source_version=document.source_version,
        content_digest=document.content_digest,
        signal_type="summary",
        signal_key="document-summary",
        text="Summary",
        evidence=(ProjectionSignalEvidence(chunk_id="chunk-1", quote="chunk text"),),
    )
    return ProjectDocumentCommand(
        document=document,
        chunks=(chunk,),
        profile=profile,
        signals=(signal,),
    )


def _project_folder_command() -> ProjectFolderCommand:
    return ProjectFolderCommand(
        folder=ProjectionFolder(
            tenant="tenant-1",
            folder_id="folder-1",
            source_version="folder-v1",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
            name="Startup",
            parent_folder_id="root",
        ),
        signals=(
            ProjectionFolderSignal(
                signal_id="folder-signal-1",
                tenant="tenant-1",
                folder_id="folder-1",
                source_version="folder-v1",
                signal_type="responsibility",
                signal_key="responsibility",
                text="Startup folder responsibility.",
            ),
        ),
    )


if __name__ == "__main__":
    unittest.main()
