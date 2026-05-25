from __future__ import annotations

import unittest
from contextlib import asynccontextmanager
from dataclasses import replace

from foldmind_ai_core.core.application.models.projection_commands import (
    DeleteDocumentProjectionCommand,
    DeleteFolderProjectionCommand,
    InvalidateFolderSignalsCommand,
    ProjectDocumentCommand,
    ProjectDocumentFolderRelationsCommand,
    ProjectFolderCommand,
    ProjectFolderSignalsCommand,
)
from foldmind_ai_core.core.application.errors import ProviderContractError
from foldmind_ai_core.core.application.models.vector_projection import (
    DocumentChunkVectorProjection,
    DocumentSignalVectorProjection,
    DocumentVectorProjection,
    FolderSignalVectorProjection,
    FolderVectorProjection,
    VectorWriteResult,
)
from foldmind_ai_core.core.domain.models.document_folder_relations import (
    SourceDocumentFolderRelationSnapshot,
)
from foldmind_ai_core.core.domain.models.document_signals import (
    DocumentSignal,
    DocumentSignalEvidence,
    DocumentSignalType,
)
from foldmind_ai_core.core.domain.models.document_sources import DocumentSourceState
from foldmind_ai_core.core.domain.models.folder_signals import (
    FolderSignal,
    FolderSignalType,
)
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder
from foldmind_ai_core.core.domain.models.document_index_state import DocumentIndexState
from foldmind_ai_core.core.domain.models.vector_projection_state import (
    VectorProjectionState,
)
from foldmind_ai_core.core.application.models.vector_projection import VectorProjectionSpec
from foldmind_ai_core.core.application.models.search import SearchScope
from foldmind_ai_core.core.application.services.projection.document_vector_projection_service import (  # noqa: E501
    DocumentVectorProjectionService,
)
from foldmind_ai_core.core.application.services.projection.folder_vector_projection_service import (
    FolderVectorProjectionService,
)
from foldmind_ai_core.core.application.services.projection.graph_projection_service import (
    GraphProjectionService,
)
from foldmind_ai_core.core.application.models.retrieval import (
    DocumentRetrievalResult,
    FolderRetrievalResult,
    RetrievalResult,
    SignalRetrievalResult,
)
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder
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
        self.folder_signal_input_digest_calls: list[tuple[str, str, str]] = []
        self.document_index_input_digest_calls: list[tuple[str, str, str]] = []
        self.document_signal_input_digest_calls: list[tuple[str, str, str, str]] = []
        self.document_folder_relation_calls: list[tuple[str, str, str]] = []

    async def is_current_folder_index_input_digest(
        self,
        *,
        tenant: str,
        folder_id: str,
        folder_index_input_digest: str,
    ) -> bool:
        self.folder_calls.append((tenant, folder_id, folder_index_input_digest))
        return self.folder_current

    async def is_current_document_folder_relation_snapshot(
        self,
        *,
        tenant: str,
        document_id: str,
        source_version: str,
    ) -> bool:
        self.document_folder_relation_calls.append((tenant, document_id, source_version))
        return self.folder_current

    async def is_current_document_index_input_digest(
        self,
        *,
        tenant: str,
        document_id: str,
        document_index_input_digest: str,
    ) -> bool:
        self.document_index_input_digest_calls.append(
            (tenant, document_id, document_index_input_digest)
        )
        return self.folder_current

    async def is_current_document_signal_input_digest(
        self,
        *,
        tenant: str,
        document_id: str,
        document_signal_input_digest: str,
        signal_generation_version: str,
    ) -> bool:
        self.document_signal_input_digest_calls.append(
            (tenant, document_id, document_signal_input_digest, signal_generation_version)
        )
        return self.folder_current

    async def is_current_folder_signal_input_digest(
        self,
        *,
        tenant: str,
        folder_id: str,
        folder_signal_input_digest: str,
    ) -> bool:
        self.folder_signal_input_digest_calls.append(
            (tenant, folder_id, folder_signal_input_digest)
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
        tenant: str,
        document_id: str,
    ) -> None:
        self.deleted.append(f"{tenant}:{document_id}")
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
        tenant: str,
        document_id: str,
    ) -> None:
        self.deleted.append(f"{tenant}:{document_id}")
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
        self.signals_by_document[document_id] = tuple(signal.signal_id for signal in signals)
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
        tenant: str,
        document_id: str,
    ) -> None:
        self.deleted_documents.append(f"{tenant}:{document_id}")
        self.signals_by_document.pop(document_id, None)

    def replace_folder_signals(
        self,
        *,
        tenant: str,
        folder_id: str,
        signals: tuple[FolderSignalVectorProjection, ...],
        vectors: tuple[Vector, ...],
    ) -> tuple[VectorWriteResult, ...]:
        self.delete_folder_signals(tenant=tenant, folder_id=folder_id)
        if signals:
            self.signals_by_folder[folder_id] = tuple(signal.signal_id for signal in signals)
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
        tenant: str,
        folder_id: str,
    ) -> None:
        self.deleted_folders.append(f"{tenant}:{folder_id}")
        self.signals_by_folder.pop(folder_id, None)

    def delete_stale_folder_signals(
        self,
        *,
        tenant: str,
        folder_id: str,
        current_folder_signal_input_digest: str,
    ) -> None:
        self.deleted_folders.append(
            f"{tenant}:{folder_id}@!={current_folder_signal_input_digest}"
        )
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

    def delete_folder_vector(self, *, tenant: str, folder_id: str) -> None:
        self.deleted.append(f"{tenant}:{folder_id}")
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
        document: DocumentSourceState,
        document_index: DocumentIndexState,
        signals: tuple[DocumentSignal, ...],
    ) -> None:
        self.relationships[document.document_id] = ()
        self.signals[document.document_id] = tuple(signal.signal_id for signal in signals)

    def replace_document_folder_relations(
        self,
        *,
        projection,
    ) -> None:
        self.relationships[projection.document_id] = projection.folder_ids

    def replace_folder_projection(
        self,
        *,
        folder: SourceFolder,
    ) -> None:
        self.folders[folder.folder_id] = folder.parent_folder_id

    def replace_folder_signals(
        self,
        *,
        folder: SourceFolder,
        folder_signal_input_digest: str,
        signal_generation_version: str,
        signals: tuple[FolderSignal, ...],
    ) -> None:
        self.signals[folder.folder_id] = tuple(signal.signal_id for signal in signals)

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
    ) -> dict[str, tuple[SourceFolder, ...]]:
        return {}

    def delete_document(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        self.deleted_documents.append(f"{tenant}:{document_id}")
        self.relationships.pop(document_id, None)
        self.signals.pop(document_id, None)

    def delete_folder_signals(self, *, tenant: str, folder_id: str) -> None:
        self.deleted_folder_signals.append(f"{tenant}:{folder_id}")

    def delete_stale_folder_signals(
        self,
        *,
        tenant: str,
        folder_id: str,
        current_folder_signal_input_digest: str,
    ) -> None:
        self.deleted_folder_signals.append(
            f"{tenant}:{folder_id}@!={current_folder_signal_input_digest}"
        )

    def delete_folder(self, *, tenant: str, folder_id: str) -> None:
        self.deleted_folders.append(f"{tenant}:{folder_id}")
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
        self.calls: list[tuple[str, ...]] = []
        self.projection_ledger = self

    @asynccontextmanager
    async def transaction(self):
        yield self

    async def record_document_vector_projected(
        self,
        *,
        record: VectorProjectionState,
    ) -> None:
        self.calls.append(("document_vector", record.source_id, record.point_id))

    async def replace_chunk_vector_records(
        self,
        *,
        tenant: str,
        document_id: str,
        records: tuple[VectorProjectionState, ...],
    ) -> None:
        self.calls.append(("chunk_vectors_deleted", tenant, document_id))
        self.calls.extend(
            ("chunk_vector", record.vector_item_id, record.point_id)
            for record in records
        )

    async def replace_signal_vector_records(
        self,
        *,
        tenant: str,
        document_id: str,
        records: tuple[VectorProjectionState, ...],
    ) -> None:
        self.calls.append(("signal_vectors_deleted", tenant, document_id))
        self.calls.extend(
            ("signal_vector", record.vector_item_id, record.point_id)
            for record in records
        )

    async def replace_folder_signal_vector_records(
        self,
        *,
        tenant: str,
        folder_id: str,
        records: tuple[VectorProjectionState, ...],
    ) -> None:
        self.calls.append(("folder_signal_vectors_deleted", tenant, folder_id))
        self.calls.extend(
            ("folder_signal_vector", record.vector_item_id, record.point_id)
            for record in records
        )

    async def record_folder_vector_projected(
        self,
        *,
        record: VectorProjectionState,
    ) -> None:
        self.calls.append(("folder_vector", record.source_id, record.point_id))

    async def delete_document_vector_records(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        self.calls.append(("document_vector_deleted", tenant, document_id))

    async def delete_chunk_vector_records(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        self.calls.append(("chunk_vectors_deleted", tenant, document_id))

    async def delete_signal_vector_records(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        self.calls.append(("signal_vectors_deleted", tenant, document_id))

    async def delete_folder_signal_vector_records(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> None:
        self.calls.append(("folder_signal_vectors_deleted", tenant, folder_id))

    async def delete_stale_folder_signal_vector_records(
        self,
        *,
        tenant: str,
        folder_id: str,
        current_source_input_digest: str,
    ) -> None:
        self.calls.append(
            (
                "stale_folder_signal_vectors_deleted",
                tenant,
                folder_id,
                current_source_input_digest,
            )
        )

    async def delete_folder_vector_records(self, *, tenant: str, folder_id: str) -> None:
        self.calls.append(("folder_vectors_deleted", tenant, folder_id))


def projection_spec() -> VectorProjectionSpec:
    return VectorProjectionSpec(
        embedding_model=TEST_EMBEDDING_MODEL,
        embedding_version=TEST_EMBEDDING_VERSION,
        index_schema_version=TEST_INDEX_SCHEMA_VERSION,
    )


def document_chunk_vector_service(**kwargs: object) -> DocumentVectorProjectionService:
    kwargs.setdefault("embeddings", FakeEmbeddingProvider())
    kwargs.setdefault("document_vectors", None)
    kwargs.setdefault("signal_vectors", None)
    kwargs.setdefault("projection_spec", None)
    kwargs.setdefault("source_freshness", FakeSourceFreshnessChecker())
    kwargs.setdefault("projection_ledger", FakeProjectionLedger())
    return DocumentVectorProjectionService(**kwargs)


def delete_document_chunk_vector_service(
    **kwargs: object,
) -> DocumentVectorProjectionService:
    kwargs.setdefault("embeddings", FakeEmbeddingProvider())
    kwargs.setdefault("document_vectors", None)
    kwargs.setdefault("signal_vectors", None)
    kwargs.setdefault("projection_spec", None)
    kwargs.setdefault("source_freshness", FakeSourceFreshnessChecker())
    kwargs.setdefault("projection_ledger", FakeProjectionLedger())
    return DocumentVectorProjectionService(**kwargs)


def document_vector_service(**kwargs: object) -> DocumentVectorProjectionService:
    kwargs.setdefault("chunk_vectors", None)
    kwargs.setdefault("signal_vectors", None)
    kwargs.setdefault("projection_spec", projection_spec())
    kwargs.setdefault("source_freshness", FakeSourceFreshnessChecker())
    kwargs.setdefault("projection_ledger", FakeProjectionLedger())
    return DocumentVectorProjectionService(**kwargs)


def delete_document_vector_service(**kwargs: object) -> DocumentVectorProjectionService:
    kwargs.setdefault("embeddings", FakeEmbeddingProvider())
    kwargs.setdefault("chunk_vectors", None)
    kwargs.setdefault("signal_vectors", None)
    kwargs.setdefault("projection_spec", projection_spec())
    kwargs.setdefault("source_freshness", FakeSourceFreshnessChecker())
    kwargs.setdefault("projection_ledger", FakeProjectionLedger())
    return DocumentVectorProjectionService(**kwargs)


def document_signal_vector_service(
    **kwargs: object,
) -> DocumentVectorProjectionService:
    kwargs.setdefault("chunk_vectors", None)
    kwargs.setdefault("document_vectors", None)
    kwargs.setdefault("projection_spec", projection_spec())
    kwargs.setdefault("source_freshness", FakeSourceFreshnessChecker())
    kwargs.setdefault("projection_ledger", FakeProjectionLedger())
    return DocumentVectorProjectionService(**kwargs)


def delete_document_signal_vector_service(
    **kwargs: object,
) -> DocumentVectorProjectionService:
    kwargs.setdefault("embeddings", FakeEmbeddingProvider())
    kwargs.setdefault("chunk_vectors", None)
    kwargs.setdefault("document_vectors", None)
    kwargs.setdefault("projection_spec", projection_spec())
    kwargs.setdefault("source_freshness", FakeSourceFreshnessChecker())
    kwargs.setdefault("projection_ledger", FakeProjectionLedger())
    return DocumentVectorProjectionService(**kwargs)


def folder_vector_service(**kwargs: object) -> FolderVectorProjectionService:
    kwargs.setdefault("signal_vectors", None)
    kwargs.setdefault("projection_spec", projection_spec())
    kwargs.setdefault("source_freshness", FakeSourceFreshnessChecker())
    kwargs.setdefault("projection_ledger", FakeProjectionLedger())
    return FolderVectorProjectionService(**kwargs)


def delete_folder_vector_service(**kwargs: object) -> FolderVectorProjectionService:
    kwargs.setdefault("embeddings", FakeEmbeddingProvider())
    kwargs.setdefault("signal_vectors", None)
    kwargs.setdefault("projection_spec", projection_spec())
    kwargs.setdefault("source_freshness", FakeSourceFreshnessChecker())
    kwargs.setdefault("projection_ledger", FakeProjectionLedger())
    return FolderVectorProjectionService(**kwargs)


def folder_signal_vector_service(**kwargs: object) -> FolderVectorProjectionService:
    kwargs.setdefault("folder_vectors", None)
    kwargs.setdefault("projection_spec", projection_spec())
    kwargs.setdefault("source_freshness", FakeSourceFreshnessChecker())
    kwargs.setdefault("projection_ledger", FakeProjectionLedger())
    return FolderVectorProjectionService(**kwargs)


def invalidate_folder_signal_vector_service(
    **kwargs: object,
) -> FolderVectorProjectionService:
    kwargs.setdefault("embeddings", FakeEmbeddingProvider())
    kwargs.setdefault("folder_vectors", None)
    kwargs.setdefault("projection_spec", projection_spec())
    kwargs.setdefault("source_freshness", FakeSourceFreshnessChecker())
    kwargs.setdefault("projection_ledger", FakeProjectionLedger())
    return FolderVectorProjectionService(**kwargs)


def delete_folder_signal_vector_service(
    **kwargs: object,
) -> FolderVectorProjectionService:
    kwargs.setdefault("embeddings", FakeEmbeddingProvider())
    kwargs.setdefault("folder_vectors", None)
    kwargs.setdefault("projection_spec", projection_spec())
    kwargs.setdefault("source_freshness", FakeSourceFreshnessChecker())
    kwargs.setdefault("projection_ledger", FakeProjectionLedger())
    return FolderVectorProjectionService(**kwargs)


def document_graph_service(**kwargs: object) -> GraphProjectionService:
    kwargs.setdefault("source_freshness", FakeSourceFreshnessChecker())
    return GraphProjectionService(**kwargs)


def document_folder_relations_graph_service(
    **kwargs: object,
) -> GraphProjectionService:
    kwargs.setdefault("source_freshness", FakeSourceFreshnessChecker())
    return GraphProjectionService(**kwargs)


def delete_document_graph_service(**kwargs: object) -> GraphProjectionService:
    kwargs.setdefault("source_freshness", FakeSourceFreshnessChecker())
    return GraphProjectionService(**kwargs)


def folder_graph_service(**kwargs: object) -> GraphProjectionService:
    kwargs.setdefault("source_freshness", FakeSourceFreshnessChecker())
    return GraphProjectionService(**kwargs)


def folder_signals_graph_service(**kwargs: object) -> GraphProjectionService:
    kwargs.setdefault("source_freshness", FakeSourceFreshnessChecker())
    return GraphProjectionService(**kwargs)


def invalidate_folder_signals_graph_service(
    **kwargs: object,
) -> GraphProjectionService:
    kwargs.setdefault("source_freshness", FakeSourceFreshnessChecker())
    return GraphProjectionService(**kwargs)


def delete_folder_graph_service(**kwargs: object) -> GraphProjectionService:
    kwargs.setdefault("source_freshness", FakeSourceFreshnessChecker())
    return GraphProjectionService(**kwargs)


class ProjectionServiceTests(unittest.IsolatedAsyncioTestCase):
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
        with self.assertRaises(InvalidInputError):
            VectorProjectionSpec(
                embedding_model=None,  # type: ignore[arg-type]
                embedding_version=TEST_EMBEDDING_VERSION,
                index_schema_version=TEST_INDEX_SCHEMA_VERSION,
            )

    async def test_project_document_command_projects_each_target_independently(
        self,
    ) -> None:
        embeddings = FakeEmbeddingProvider()
        chunk_vectors = FakeDocumentChunkVectorStore()
        document_vectors = FakeDocumentVectorStore()
        signal_vectors = FakeSignalVectorStore()
        graph = FakeGraphStore()
        ledger = FakeProjectionLedger()
        command = _project_document_command()
        chunk_projection = document_chunk_vector_service(
            embeddings=embeddings,
            chunk_vectors=chunk_vectors,
            projection_ledger=ledger,
        )
        document_projection = document_vector_service(
            embeddings=embeddings,
            document_vectors=document_vectors,
            projection_ledger=ledger,
        )
        signal_projection = document_signal_vector_service(
            embeddings=embeddings,
            signal_vectors=signal_vectors,
            projection_ledger=ledger,
        )
        graph_projection = document_graph_service(
            graph=graph,
        )

        for _ in range(5):
            await chunk_projection.project_document_chunks(command)
            await document_projection.project_document_vector(command)
            await signal_projection.project_document_signals(command)
            await graph_projection.project_document_graph(command)

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

    async def test_empty_chunk_projection_skips_embedding_call(self) -> None:
        embeddings = FakeEmbeddingProvider()
        chunk_vectors = FakeDocumentChunkVectorStore()
        ledger = FakeProjectionLedger()

        await document_chunk_vector_service(
            embeddings=embeddings,
            chunk_vectors=chunk_vectors,
            projection_ledger=ledger,
        ).project_document_chunks(replace(_project_document_command(), chunks=()))

        self.assertEqual(embeddings.texts, [])
        self.assertEqual(chunk_vectors.chunks_by_document, {"doc-1": ()})
        self.assertEqual(
            ledger.calls,
            [("chunk_vectors_deleted", "tenant-1", "doc-1")],
        )

    async def test_empty_document_signal_projection_skips_embedding_call(self) -> None:
        embeddings = FakeEmbeddingProvider()
        signal_vectors = FakeSignalVectorStore()
        ledger = FakeProjectionLedger()

        await document_signal_vector_service(
            embeddings=embeddings,
            signal_vectors=signal_vectors,
            projection_ledger=ledger,
        ).project_document_signals(replace(_project_document_command(), signals=()))

        self.assertEqual(embeddings.texts, [])
        self.assertEqual(signal_vectors.signals_by_document, {"doc-1": ()})
        self.assertEqual(
            ledger.calls,
            [("signal_vectors_deleted", "tenant-1", "doc-1")],
        )

    async def test_empty_folder_signal_projection_skips_embedding_call(self) -> None:
        embeddings = FakeEmbeddingProvider()
        signal_vectors = FakeSignalVectorStore()
        ledger = FakeProjectionLedger()

        await folder_signal_vector_service(
            embeddings=embeddings,
            signal_vectors=signal_vectors,
            projection_ledger=ledger,
        ).project_folder_signals(
            replace(_project_folder_signals_command(), signals=())
        )

        self.assertEqual(embeddings.texts, [])
        self.assertEqual(signal_vectors.signals_by_folder, {})
        self.assertEqual(signal_vectors.deleted_folders, ["tenant-1:folder-1"])
        self.assertEqual(
            ledger.calls,
            [("folder_signal_vectors_deleted", "tenant-1", "folder-1")],
        )

    async def test_vector_projection_rejects_embedding_count_mismatch(self) -> None:
        command = _project_document_command()

        with self.assertRaises(ProviderContractError):
            await document_chunk_vector_service(
                embeddings=ShortEmbeddingProvider(),
                chunk_vectors=FakeDocumentChunkVectorStore(),
            ).project_document_chunks(command)

        with self.assertRaises(ProviderContractError):
            await document_vector_service(
                embeddings=ShortEmbeddingProvider(),
                document_vectors=FakeDocumentVectorStore(),
            ).project_document_vector(command)

        with self.assertRaises(ProviderContractError):
            await document_signal_vector_service(
                embeddings=ShortEmbeddingProvider(),
                signal_vectors=FakeSignalVectorStore(),
            ).project_document_signals(command)

        with self.assertRaises(ProviderContractError):
            await folder_vector_service(
                embeddings=ShortEmbeddingProvider(),
                folder_vectors=FakeFolderVectorStore(),
            ).project_folder_vector(
                ProjectFolderCommand(
                    folder=SourceFolder(
                        tenant="tenant-1",
                        folder_id="folder-1",
                        source_version="folder-v1",
                        created_at="2026-05-01T10:00:00+09:00",
                        updated_at="2026-05-02T11:00:00+09:00",
                        name="Startup",
                    )
                )
            )

    async def test_delete_events_project_each_target_independently(self) -> None:
        chunk_vectors = FakeDocumentChunkVectorStore()
        document_vectors = FakeDocumentVectorStore()
        signal_vectors = FakeSignalVectorStore()
        folder_vectors = FakeFolderVectorStore()
        graph = FakeGraphStore()
        ledger = FakeProjectionLedger()
        document_command = DeleteDocumentProjectionCommand(
            tenant="tenant-1",
            document_id="doc-1",
            affected_folder_ids=("folder-1", "folder-2"),
        )
        folder_command = DeleteFolderProjectionCommand(
            tenant="tenant-1",
            folder_id="folder-1",
        )

        for _ in range(2):
            await delete_document_chunk_vector_service(
                chunk_vectors=chunk_vectors,
                projection_ledger=ledger,
            ).delete_document_chunks(document_command)
            await delete_document_vector_service(
                document_vectors=document_vectors,
                projection_ledger=ledger,
            ).delete_document_vector(document_command)
            await delete_document_signal_vector_service(
                signal_vectors=signal_vectors,
                projection_ledger=ledger,
            ).delete_document_signals(document_command)
            await delete_document_graph_service(
                graph=graph,
            ).delete_document_graph(document_command)
            await delete_folder_vector_service(
                folder_vectors=folder_vectors,
                projection_ledger=ledger,
            ).delete_folder_vector(folder_command)
            await delete_folder_signal_vector_service(
                signal_vectors=signal_vectors,
                projection_ledger=ledger,
            ).delete_folder_signals(folder_command)
            await delete_folder_graph_service(
                graph=graph,
            ).delete_folder_graph(folder_command)

        self.assertEqual(chunk_vectors.deleted, ["tenant-1:doc-1", "tenant-1:doc-1"])
        self.assertEqual(document_vectors.deleted, ["tenant-1:doc-1", "tenant-1:doc-1"])
        self.assertEqual(
            signal_vectors.deleted_documents,
            ["tenant-1:doc-1", "tenant-1:doc-1"],
        )
        self.assertEqual(
            signal_vectors.deleted_folders,
            ["tenant-1:folder-1", "tenant-1:folder-1"],
        )
        self.assertEqual(graph.deleted_documents, ["tenant-1:doc-1", "tenant-1:doc-1"])
        self.assertEqual(graph.deleted_folder_signals, [])
        self.assertEqual(
            folder_vectors.deleted,
            ["tenant-1:folder-1", "tenant-1:folder-1"],
        )
        self.assertEqual(
            graph.deleted_folders,
            ["tenant-1:folder-1", "tenant-1:folder-1"],
        )
        self.assertEqual(
            ledger.calls.count(("chunk_vectors_deleted", "tenant-1", "doc-1")),
            2,
        )
        self.assertEqual(
            ledger.calls.count(("document_vector_deleted", "tenant-1", "doc-1")),
            2,
        )
        self.assertEqual(
            ledger.calls.count(("signal_vectors_deleted", "tenant-1", "doc-1")),
            2,
        )
        self.assertEqual(
            ledger.calls.count(
                ("folder_signal_vectors_deleted", "tenant-1", "folder-2")
            ),
            0,
        )
        self.assertEqual(
            ledger.calls.count(("folder_vectors_deleted", "tenant-1", "folder-1")),
            2,
        )
        self.assertEqual(
            ledger.calls.count(
                ("folder_signal_vectors_deleted", "tenant-1", "folder-1")
            ),
            2,
        )

    async def test_project_folder_command_projects_each_target_independently(
        self,
    ) -> None:
        embeddings = FakeEmbeddingProvider()
        signal_vectors = FakeSignalVectorStore()
        folder_vectors = FakeFolderVectorStore()
        graph = FakeGraphStore()
        ledger = FakeProjectionLedger()
        folder_command = _project_folder_command()
        folder_signals_command = _project_folder_signals_command()

        await folder_vector_service(
            embeddings=embeddings,
            folder_vectors=folder_vectors,
            projection_ledger=ledger,
        ).project_folder_vector(folder_command)
        await folder_signal_vector_service(
            embeddings=embeddings,
            signal_vectors=signal_vectors,
            projection_ledger=ledger,
        ).project_folder_signals(folder_signals_command)
        await folder_graph_service(
            graph=graph,
        ).project_folder_graph(folder_command)
        await folder_signals_graph_service(
            graph=graph,
        ).project_folder_signals(folder_signals_command)

        self.assertEqual(folder_vectors.folders, {"folder-1": "folder-v1"})
        self.assertEqual(
            signal_vectors.signals_by_folder,
            {"folder-1": ("folder-signal-1",)},
        )
        self.assertEqual(graph.folders, {"folder-1": "root"})
        self.assertEqual(
            graph.signals,
            {"folder-1": ("folder-signal-1",)},
        )
        self.assertEqual(
            embeddings.texts,
            [
                "Startup",
                "Startup folder responsibility.",
            ],
        )
        self.assertIn(("folder_vector", "folder-1", "folder-1"), ledger.calls)
        self.assertIn(
            ("folder_signal_vector", "folder-signal-1", "folder:folder-signal-1"),
            ledger.calls,
        )

    async def test_folder_signal_projection_skips_stale_source(self) -> None:
        embeddings = FakeEmbeddingProvider()
        signal_vectors = FakeSignalVectorStore()
        ledger = FakeProjectionLedger()
        source_freshness = FakeSourceFreshnessChecker(folder_current=False)
        command = _project_folder_signals_command()

        await folder_signal_vector_service(
            embeddings=embeddings,
            signal_vectors=signal_vectors,
            projection_ledger=ledger,
            source_freshness=source_freshness,
        ).project_folder_signals(command)

        self.assertEqual(embeddings.texts, [])
        self.assertEqual(signal_vectors.signals_by_folder, {})
        self.assertEqual(signal_vectors.deleted_folders, [])
        self.assertEqual(ledger.calls, [])
        self.assertEqual(
            source_freshness.folder_signal_input_digest_calls,
            [("tenant-1", "folder-1", "folder-signal-input-v1")],
        )

    async def test_document_folder_relation_graph_projection_replaces_edges(
        self,
    ) -> None:
        graph = FakeGraphStore()
        source_freshness = FakeSourceFreshnessChecker()
        command = ProjectDocumentFolderRelationsCommand(
            folder_relation_snapshot=SourceDocumentFolderRelationSnapshot(
                tenant="tenant-1",
                document_id="doc-1",
                source_version="v1",
                folder_ids=("folder-1",),
            )
        )

        await document_folder_relations_graph_service(
            graph=graph,
            source_freshness=source_freshness,
        ).project_document_folder_relations(command)

        self.assertEqual(graph.relationships["doc-1"], ("folder-1",))
        self.assertEqual(
            source_freshness.document_folder_relation_calls,
            [("tenant-1", "doc-1", "v1")],
        )

    async def test_folder_signal_invalidation_deletes_previous_revision_vectors(
        self,
    ) -> None:
        signal_vectors = FakeSignalVectorStore()
        projection_ledger = FakeProjectionLedger()
        signal_vectors.signals_by_folder["folder-1"] = ("old-signal",)

        await invalidate_folder_signal_vector_service(
            signal_vectors=signal_vectors,
            projection_ledger=projection_ledger,
        ).invalidate_folder_signals(
            InvalidateFolderSignalsCommand(
                tenant="tenant-1",
                folder_id="folder-1",
                folder_signal_input_digest="folder-signal-input-v2",
            )
        )

        self.assertEqual(signal_vectors.signals_by_folder, {})
        self.assertEqual(
            signal_vectors.deleted_folders,
            ["tenant-1:folder-1@!=folder-signal-input-v2"],
        )
        self.assertEqual(
            projection_ledger.calls,
            [
                (
                    "stale_folder_signal_vectors_deleted",
                    "tenant-1",
                    "folder-1",
                    "folder-signal-input-v2",
                )
            ],
        )

    async def test_folder_signal_invalidation_deletes_previous_revision_graph(
        self,
    ) -> None:
        graph = FakeGraphStore()

        await invalidate_folder_signals_graph_service(graph=graph).invalidate_folder_signals(
            InvalidateFolderSignalsCommand(
                tenant="tenant-1",
                folder_id="folder-1",
                folder_signal_input_digest="folder-signal-input-v2",
            )
        )

        self.assertEqual(
            graph.deleted_folder_signals,
            ["tenant-1:folder-1@!=folder-signal-input-v2"],
        )


def _project_document_command() -> ProjectDocumentCommand:
    document = DocumentSourceState(
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
        source_input_digest="index-input-v1",
        vector_input_digest="vector-input-v1",
        created_at=document.created_at,
        updated_at=document.updated_at,
        chunk_id="chunk-1",
        chunk_index=0,
        text="chunk text",
        text_hash="hash-1",
        start_offset=0,
        end_offset=10,
        embedding_model="embedding",
        embedding_version="v1",
        index_schema_version="schema-v1",
    )
    document_index = DocumentIndexState(
        document_id=document.document_id,
        document_index_input_digest=chunk.source_input_digest,
        document_signal_input_digest=chunk.source_input_digest,
    )
    signal = DocumentSignal(
        signal_id="signal-1",
        tenant=document.tenant,
        document_type=document.document_type,
        document_id=document.document_id,
        source_version=document.source_version,
        document_signal_input_digest=chunk.source_input_digest,
        signal_type=DocumentSignalType.SUMMARY,
        signal_key="document-summary",
        text="Summary",
        extractor_name="test-extractor",
        extractor_version="test-extractor-v1",
        evidence=(DocumentSignalEvidence(chunk_id="chunk-1", quote="chunk text"),),
    )
    return ProjectDocumentCommand(
        document=document,
        chunks=(chunk,),
        document_index=document_index,
        signals=(signal,),
    )


def _project_folder_command() -> ProjectFolderCommand:
    return ProjectFolderCommand(
        folder=SourceFolder(
            tenant="tenant-1",
            folder_id="folder-1",
            source_version="folder-v1",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
            name="Startup",
            parent_folder_id="root",
        ),
    )


def _project_folder_signals_command() -> ProjectFolderSignalsCommand:
    return ProjectFolderSignalsCommand(
        folder=_project_folder_command().folder,
        folder_signal_input_digest="folder-signal-input-v1",
        signals=(
            FolderSignal(
                signal_id="folder-signal-1",
                tenant="tenant-1",
                folder_id="folder-1",
                source_version="folder-v1",
                signal_type=FolderSignalType.RESPONSIBILITY,
                signal_key="responsibility",
                text="Startup folder responsibility.",
                extractor_name="folder-extractor",
                extractor_version="folder-extractor-v1",
                folder_signal_input_digest="folder-signal-input-v1",
            ),
        ),
    )


if __name__ == "__main__":
    unittest.main()
