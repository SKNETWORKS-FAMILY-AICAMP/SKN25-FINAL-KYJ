from __future__ import annotations

import unittest
from contextlib import asynccontextmanager
from datetime import datetime

from foldmind_ai_core.core.application.errors import ProviderContractError
from foldmind_ai_core.core.application.models.vector_projection import DocumentVectorProjection
from foldmind_ai_core.core.application.models.search import (
    RequestContext,
    SearchScope,
    SearchSort,
)
from foldmind_ai_core.core.application.models.retrieval import RetrievalQuery
from foldmind_ai_core.core.application.models.retrieval import DocumentTitleKeywordMatch
from foldmind_ai_core.core.application.services.retrieval.document_retrieval_service import (
    DocumentRetrievalService,
)
from foldmind_ai_core.core.application.services.retrieval.document_search_service import (
    DocumentSearchService,
)
from foldmind_ai_core.core.application.services.retrieval.policy import (
    DocumentRetrievalConfig,
    DocumentRetrievalPolicy,
)
from foldmind_ai_core.core.application.services.retrieval.scope_resolver import (
    RelationshipScopeResolver,
)
from foldmind_ai_core.core.domain.models.document_chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.document_sources import DocumentSourceState
from foldmind_ai_core.core.application.models.retrieval import (
    DocumentRetrievalResult,
    RetrievalResult,
    RetrievedDocument,
)
from foldmind_ai_core.shared.types import Vector
from foldmind_ai_core.shared.validation import InvalidInputError


class FakeEmbeddingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def embed_texts(self, texts: list[str]) -> list[Vector]:
        self.calls += 1
        return [[float(len(text))] for text in texts]


class ShortEmbeddingProvider:
    def embed_texts(self, texts: list[str]) -> list[Vector]:
        return []


class CapturingChunkVectorStore:
    def __init__(self, results: list[RetrievalResult]) -> None:
        self.results = results
        self.scopes: list[SearchScope | None] = []

    def similarity_search(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[RetrievalResult]:
        self.scopes.append(scope)
        return self.results[:top_k]


class FakeDocumentVectorStore:
    def __init__(self, results: list[DocumentRetrievalResult]) -> None:
        self.results = results

    def similarity_search(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[DocumentRetrievalResult]:
        return self.results[:top_k]


class FakeDocumentVectorStores:
    def __init__(
        self,
        *,
        chunks: CapturingChunkVectorStore,
        documents: FakeDocumentVectorStore | None = None,
    ) -> None:
        self.chunks = chunks
        self.documents = documents

    def replace_document_chunks(
        self,
        *,
        tenant: str,
        document_id: str,
        chunks: tuple[DocumentChunk, ...],
        vectors: tuple[Vector, ...],
    ) -> None:
        raise AssertionError("Document chunk writes are not expected in these tests.")

    def upsert_document_vector(
        self,
        *,
        projection: DocumentVectorProjection,
        vector: Vector,
    ) -> None:
        raise AssertionError("Document vector writes are not expected in these tests.")

    def delete_document_chunks(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        raise AssertionError("Document chunk deletes are not expected in these tests.")

    def delete_document_vector(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        raise AssertionError("Document vector deletes are not expected in these tests.")

    def search_chunks(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[RetrievalResult]:
        return self.chunks.similarity_search(
            tenant=tenant,
            query_vector=query_vector,
            top_k=top_k,
            scope=scope,
        )

    def search_documents(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[DocumentRetrievalResult]:
        if self.documents is None:
            return []
        return self.documents.similarity_search(
            tenant=tenant,
            query_vector=query_vector,
            top_k=top_k,
            scope=scope,
        )


class FakeDocumentSourceRepository:
    def __init__(
        self,
        *,
        title_matches: tuple[DocumentTitleKeywordMatch, ...] = (),
    ) -> None:
        self.title_matches = title_matches

    async def get_current_document_sources(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
    ) -> tuple[DocumentSourceState, ...]:
        return tuple(
            DocumentSourceState(
                tenant=tenant,
                document_type="document",
                document_id=document_id,
                source_version="v1",
                title=document_id,
                created_at="2026-05-01T10:00:00+09:00",
                updated_at="2026-05-02T11:00:00+09:00",
                content_digest=f"content-digest-{document_id}",
                content_size_bytes=len(document_id.encode("utf-8")),
            )
            for document_id in document_ids
        )

    async def document_ids_for_scope(
        self,
        *,
        tenant: str,
        document_type: str | None,
        document_id: str | None,
        document_ids: tuple[str, ...],
        created_at: datetime | None,
        updated_at: datetime | None,
        metadata_filter: dict[str, object] | None,
    ) -> tuple[str, ...]:
        if document_ids:
            return document_ids
        if document_id is not None:
            return (document_id,)
        return ()

    async def search_titles_by_keyword(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        document_type: str | None,
        document_id: str | None,
        document_ids: tuple[str, ...],
        created_at: datetime | None,
        updated_at: datetime | None,
        metadata_filter: dict[str, object] | None,
    ) -> tuple[tuple[DocumentSourceState, float], ...]:
        return tuple((match.source, match.score) for match in self.title_matches[:top_k])


class FakeDocumentProjectionRepository:
    def __init__(
        self,
        *,
        title_chunks: tuple[DocumentChunk, ...] = (),
        chunk_results: list[RetrievalResult] | None = None,
    ) -> None:
        self.title_chunks = title_chunks
        self.chunk_results = chunk_results or []
        self.scopes: list[SearchScope] = []

    async def get_first_chunks_for_documents(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
        limit: int,
    ) -> tuple[DocumentChunk, ...]:
        document_id_set = set(document_ids)
        return tuple(
            chunk
            for chunk in self.title_chunks
            if chunk.document_id in document_id_set
        )[:limit]

    async def search_chunks_by_keyword(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        document_id: str | None,
        document_ids: tuple[str, ...],
    ) -> tuple[tuple[DocumentChunk, float], ...]:
        self.scopes.append(SearchScope(document_id=document_id, document_ids=document_ids))
        return tuple(
            (result.chunk, result.score)
            for result in self.chunk_results[:top_k]
        )


class FakeDocumentRelationRepository:
    async def document_ids_for_folders(
        self,
        *,
        tenant: str,
        folder_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        return ()


class FakeRetrievalReadSession:
    def __init__(
        self,
        document_sources: FakeDocumentSourceRepository,
        document_projections: FakeDocumentProjectionRepository,
    ) -> None:
        self.document_sources = document_sources
        self.document_projections = document_projections
        self.document_relations = FakeDocumentRelationRepository()
        self.folder_sources = object()


class FakeRetrievalReadSessionProvider:
    def __init__(
        self,
        document_sources: FakeDocumentSourceRepository,
        document_projections: FakeDocumentProjectionRepository,
    ) -> None:
        self.document_sources = document_sources
        self.document_projections = document_projections

    @asynccontextmanager
    async def session(self):
        yield FakeRetrievalReadSession(
            self.document_sources,
            self.document_projections,
        )


class FakeGraphStore:
    def __init__(
        self,
        results: list[DocumentRetrievalResult],
        *,
        scoped_document_ids: tuple[str, ...] | None = None,
    ) -> None:
        self.results = results
        self.scoped_document_ids = scoped_document_ids

    def replace_document_projection(
        self,
        *,
        relationships: object,
        signals: object,
    ) -> None:
        raise AssertionError("Graph projection writes are not expected in these tests.")

    def replace_document_folder_relations(self, *, projection: object) -> None:
        raise AssertionError("Graph projection writes are not expected in these tests.")

    def replace_folder_projection(self, *, relationships: object) -> None:
        raise AssertionError("Folder projection writes are not expected in these tests.")

    def replace_folder_signals(self, *, signals: object) -> None:
        raise AssertionError("Folder projection writes are not expected in these tests.")

    def delete_document(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        raise AssertionError("Graph document deletes are not expected in these tests.")

    def delete_folder(self, *, tenant: str, folder_id: str) -> None:
        raise AssertionError("Graph folder deletes are not expected in these tests.")

    def delete_folder_signals(self, *, tenant: str, folder_id: str) -> None:
        raise AssertionError("Folder signal deletes are not expected in these tests.")

    def delete_stale_folder_signals(
        self,
        *,
        tenant: str,
        folder_id: str,
        current_folder_signal_input_digest: str,
    ) -> None:
        raise AssertionError("Folder signal deletes are not expected in these tests.")

    def graph_search(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[DocumentRetrievalResult]:
        return self.results[:top_k]

    def document_ids_for_scope(self, *, tenant: str, scope: SearchScope) -> tuple[str, ...]:
        if self.scoped_document_ids is not None:
            return self.scoped_document_ids
        return scope.document_ids

    def folders_for_documents(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
    ) -> dict[str, tuple[object, ...]]:
        return {}


def make_document(
    document_id: str,
    score_text: str = "",
    *,
    document_type: str = "document",
) -> RetrievedDocument:
    return RetrievedDocument(
        tenant="tenant-1",
        document_type=document_type,
        document_id=document_id,
        source_version="v1",
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        snippet=score_text or document_id,
    )


def make_source_record(document_id: str) -> DocumentSourceState:
    return DocumentSourceState(
        tenant="tenant-1",
        document_type="document",
        document_id=document_id,
        source_version="v1",
        title=document_id,
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        content_digest=f"content-digest-{document_id}",
        content_size_bytes=len(document_id.encode("utf-8")),
    )


def make_result(document_id: str, chunk_id: str, score: float) -> RetrievalResult:
    text = f"{document_id} startup evidence"
    return RetrievalResult(
        chunk=DocumentChunk(
            tenant="tenant-1",
            document_type="document",
            document_id=document_id,
            source_version="v1",
            document_index_input_digest="index-input-v1",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
            chunk_id=chunk_id,
            chunk_index=0,
            text=text,
            start_offset=0,
            end_offset=len(text),
        ),
        score=score,
    )


def make_document_search_service(
    *,
    embeddings: FakeEmbeddingProvider,
    documents: FakeDocumentVectorStores,
    graph: FakeGraphStore,
    document_sources: FakeDocumentSourceRepository | None = None,
    document_projections: FakeDocumentProjectionRepository | None = None,
    config: DocumentRetrievalConfig,
) -> DocumentSearchService:
    return DocumentSearchService(
        retrieval=DocumentRetrievalService(
            embeddings=embeddings,
            chunk_vectors=documents,
            document_vectors=documents,
            graph=graph,
            retrieval_reads=FakeRetrievalReadSessionProvider(
                document_sources or FakeDocumentSourceRepository(),
                document_projections or FakeDocumentProjectionRepository(),
            ),
            config=config,
        ),
        scope_resolver=RelationshipScopeResolver(graph=graph),
    )


class DocumentRetrievalTests(unittest.IsolatedAsyncioTestCase):
    def test_document_retrieval_config_rejects_malformed_numeric_options(self) -> None:
        with self.assertRaises(InvalidInputError):
            DocumentRetrievalConfig(top_k=True)
        with self.assertRaises(InvalidInputError):
            DocumentRetrievalConfig(document_top_k=0)
        with self.assertRaises(InvalidInputError):
            DocumentRetrievalConfig(graph_top_k=1.5)
        with self.assertRaises(InvalidInputError):
            DocumentRetrievalConfig(comprehensive_top_k=-1)
        with self.assertRaises(InvalidInputError):
            DocumentRetrievalConfig(both_sources_bonus=float("nan"))

    def test_duplicate_document_candidates_do_not_count_as_distinct_sources(self) -> None:
        ranked = DocumentRetrievalPolicy(
            DocumentRetrievalConfig(both_sources_bonus=0.15)
        ).rank_document_candidates(
            document_results=[
                DocumentRetrievalResult(document=make_document("doc-a"), score=0.4),
                DocumentRetrievalResult(document=make_document("doc-a"), score=0.3),
                DocumentRetrievalResult(document=make_document("doc-b"), score=0.9),
            ],
            graph_results=[],
        )

        self.assertEqual([result.document.document_id for result in ranked], ["doc-b", "doc-a"])
        self.assertEqual(ranked[1].score, 0.4)

    def test_document_candidates_ignore_blank_ids_and_non_finite_scores(self) -> None:
        ranked = DocumentRetrievalPolicy(
            DocumentRetrievalConfig(both_sources_bonus=0.15)
        ).rank_document_candidates(
            document_results=[
                DocumentRetrievalResult(document=make_document(" "), score=0.9),
                DocumentRetrievalResult(
                    document=make_document("doc-invalid"),
                    score=float("nan"),
                ),
                DocumentRetrievalResult(document=make_document("doc-valid"), score=0.4),
            ],
            graph_results=[
                DocumentRetrievalResult(
                    document=make_document("doc-graph-invalid"),
                    score=float("inf"),
                )
            ],
        )

        self.assertEqual(
            [result.document.document_id for result in ranked],
            ["doc-valid"],
        )

    async def test_blank_document_search_returns_empty_result_without_provider_call(
        self,
    ) -> None:
        embeddings = FakeEmbeddingProvider()
        chunks = CapturingChunkVectorStore([make_result("doc-valid", "chunk-1", 0.7)])
        document_port = FakeDocumentVectorStores(chunks=chunks)

        results = await make_document_search_service(
            embeddings=embeddings,
            documents=document_port,
            graph=FakeGraphStore([]),
            config=DocumentRetrievalConfig(top_k=3),
        ).search(
            RetrievalQuery(
                text="   ",
                request_context=RequestContext(
                    tenant="tenant-1",
                    requested_at="2026-05-17T09:30:00+09:00",
                ),
            )
        )

        self.assertEqual(results, ())
        self.assertEqual(embeddings.calls, 0)
        self.assertEqual(chunks.scopes, [])

    async def test_chunk_results_ignore_blank_ids_and_non_finite_scores(self) -> None:
        chunks = CapturingChunkVectorStore(
            [
                make_result(" ", "blank:chunk:0", 0.9),
                make_result("doc-invalid", "doc-invalid:chunk:0", float("nan")),
                make_result("doc-valid", "doc-valid:chunk:0", 0.7),
            ]
        )
        document_port = FakeDocumentVectorStores(chunks=chunks)

        results = await make_document_search_service(
            embeddings=FakeEmbeddingProvider(),
            documents=document_port,
            graph=FakeGraphStore([]),
            config=DocumentRetrievalConfig(top_k=3),
        ).search(
            RetrievalQuery(
                text="창업 관련 문서",
                request_context=RequestContext(
                    tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"
                ),
            )
        )

        self.assertEqual(
            [result.chunk.document_id for result in results],
            ["doc-valid"],
        )

    def test_document_candidates_receive_cross_source_bonus_once(self) -> None:
        ranked = DocumentRetrievalPolicy(
            DocumentRetrievalConfig(both_sources_bonus=0.15)
        ).rank_document_candidates(
            document_results=[
                DocumentRetrievalResult(document=make_document("doc-a"), score=0.5),
            ],
            graph_results=[
                DocumentRetrievalResult(document=make_document("doc-a"), score=0.7),
                DocumentRetrievalResult(document=make_document("doc-a"), score=0.6),
            ],
        )

        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0].document.document_id, "doc-a")
        self.assertEqual(ranked[0].score, 0.85)

    def test_document_candidate_ties_keep_first_source_order(self) -> None:
        ranked = DocumentRetrievalPolicy(
            DocumentRetrievalConfig(both_sources_bonus=0.0)
        ).rank_document_candidates(
            document_results=[
                DocumentRetrievalResult(document=make_document("doc-a"), score=0.7),
                DocumentRetrievalResult(document=make_document("doc-b"), score=0.7),
            ],
            graph_results=[
                DocumentRetrievalResult(document=make_document("doc-c"), score=0.7),
            ],
        )

        self.assertEqual(
            [result.document.document_id for result in ranked],
            ["doc-a", "doc-b", "doc-c"],
        )

    async def test_qdrant_documents_and_graph_candidates_constrain_chunk_search(
        self,
    ) -> None:
        chunks = CapturingChunkVectorStore(
            [
                make_result("doc-a", "doc-a:chunk:0", 0.9),
                make_result("doc-b", "doc-b:chunk:0", 0.8),
            ]
        )

        document_port = FakeDocumentVectorStores(
            chunks=chunks,
            documents=FakeDocumentVectorStore(
                [DocumentRetrievalResult(document=make_document("doc-a"), score=0.7)]
            ),
        )
        results = await make_document_search_service(
            embeddings=FakeEmbeddingProvider(),
            documents=document_port,
            graph=FakeGraphStore(
                [DocumentRetrievalResult(document=make_document("doc-b"), score=0.6)]
            ),
            config=DocumentRetrievalConfig(top_k=2),
        ).search(
            RetrievalQuery(
                text="창업 관련 문서",
                request_context=RequestContext(
                    tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"
                ),
            )
        )

        self.assertEqual(
            [result.chunk.document_id for result in results],
            ["doc-a", "doc-b"],
        )
        self.assertEqual(chunks.scopes[0].document_ids, ("doc-a", "doc-b"))

    async def test_explicit_document_scope_is_not_replaced_by_candidates(self) -> None:
        chunks = CapturingChunkVectorStore([make_result("doc-a", "doc-a:chunk:0", 0.9)])
        document_port = FakeDocumentVectorStores(
            chunks=chunks,
            documents=FakeDocumentVectorStore(
                [
                    DocumentRetrievalResult(
                        document=make_document("doc-b", document_type="note"),
                        score=0.7,
                    )
                ]
            ),
        )

        await make_document_search_service(
            embeddings=FakeEmbeddingProvider(),
            documents=document_port,
            graph=FakeGraphStore(
                [DocumentRetrievalResult(document=make_document("doc-c"), score=0.6)]
            ),
            config=DocumentRetrievalConfig(top_k=1),
        ).search(
            RetrievalQuery(
                text="창업 관련 문서",
                request_context=RequestContext(
                    tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"
                ),
                scope=SearchScope(document_id="doc-a"),
            )
        )

        self.assertEqual(chunks.scopes[0].document_id, "doc-a")
        self.assertEqual(chunks.scopes[0].document_ids, ())
        self.assertIsNone(chunks.scopes[0].document_type)

    async def test_mixed_document_type_candidates_do_not_force_first_type(self) -> None:
        chunks = CapturingChunkVectorStore(
            [
                make_result("doc-a", "doc-a:chunk:0", 0.9),
                make_result("note-b", "note-b:chunk:0", 0.8),
            ]
        )
        document_port = FakeDocumentVectorStores(
            chunks=chunks,
            documents=FakeDocumentVectorStore(
                [
                    DocumentRetrievalResult(
                        document=make_document("doc-a", document_type="document"),
                        score=0.7,
                    )
                ]
            ),
        )

        await make_document_search_service(
            embeddings=FakeEmbeddingProvider(),
            documents=document_port,
            graph=FakeGraphStore(
                [
                    DocumentRetrievalResult(
                        document=make_document("note-b", document_type="note"),
                        score=0.6,
                    )
                ]
            ),
            config=DocumentRetrievalConfig(top_k=2),
        ).search(
            RetrievalQuery(
                text="창업 관련 문서",
                request_context=RequestContext(
                    tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"
                ),
            )
        )

        self.assertIsNone(chunks.scopes[0].document_type)
        self.assertEqual(chunks.scopes[0].document_ids, ("doc-a", "note-b"))

    async def test_relationship_scope_uses_resolved_document_set_without_readding_anchor(
        self,
    ) -> None:
        chunks = CapturingChunkVectorStore([make_result("doc-b", "doc-b:chunk:0", 0.9)])
        document_port = FakeDocumentVectorStores(chunks=chunks)

        await make_document_search_service(
            embeddings=FakeEmbeddingProvider(),
            documents=document_port,
            graph=FakeGraphStore([], scoped_document_ids=("doc-b",)),
            config=DocumentRetrievalConfig(top_k=1),
        ).search(
            RetrievalQuery(
                text="창업 관련 문서",
                request_context=RequestContext(
                    tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"
                ),
                scope=SearchScope(
                    document_id="doc-a",
                    document_ids=("doc-b",),
                    folder_ids=("folder-1",),
                    created_at=datetime.fromisoformat("2026-05-01T00:00:00+09:00"),
                    sort=SearchSort(field="created_at", direction="desc"),
                ),
            )
        )

        self.assertIsNone(chunks.scopes[0].document_id)
        self.assertEqual(chunks.scopes[0].document_ids, ("doc-b",))
        self.assertEqual(chunks.scopes[0].folder_ids, ())
        self.assertEqual(
            chunks.scopes[0].created_at,
            datetime.fromisoformat("2026-05-01T00:00:00+09:00"),
        )
        self.assertEqual(chunks.scopes[0].sort.field, "created_at")
        self.assertEqual(chunks.scopes[0].sort.direction, "desc")

    async def test_keyword_results_are_merged_with_dense_chunk_results(self) -> None:
        document_port = FakeDocumentVectorStores(
            chunks=CapturingChunkVectorStore([make_result("doc-a", "doc-a:chunk:0", 0.9)]),
        )
        document_projections = FakeDocumentProjectionRepository(
            chunk_results=[make_result("doc-b", "doc-b:chunk:0", 0.8)]
        )

        results = await make_document_search_service(
            embeddings=FakeEmbeddingProvider(),
            documents=document_port,
            graph=FakeGraphStore([]),
            document_projections=document_projections,
            config=DocumentRetrievalConfig(top_k=2, keyword_top_k=1),
        ).search(
            RetrievalQuery(
                text="창업 관련 문서",
                request_context=RequestContext(
                    tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"
                ),
            )
        )

        self.assertEqual(
            {result.chunk.document_id for result in results},
            {"doc-a", "doc-b"},
        )

    async def test_title_keyword_score_is_combined_with_chunk_keyword_score(self) -> None:
        keyword_result = make_result("doc-a", "doc-a:chunk:0", 0.5)

        results = await make_document_search_service(
            embeddings=FakeEmbeddingProvider(),
            documents=FakeDocumentVectorStores(
                chunks=CapturingChunkVectorStore([]),
            ),
            graph=FakeGraphStore([]),
            document_sources=FakeDocumentSourceRepository(
                title_matches=(
                    DocumentTitleKeywordMatch(
                        source=make_source_record("doc-a"),
                        score=0.25,
                    ),
                ),
            ),
            document_projections=FakeDocumentProjectionRepository(
                title_chunks=(keyword_result.chunk,),
                chunk_results=[keyword_result],
            ),
            config=DocumentRetrievalConfig(top_k=1, keyword_top_k=5),
        ).search(
            RetrievalQuery(
                text="창업 관련 문서",
                request_context=RequestContext(
                    tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"
                ),
            )
        )

        self.assertEqual(results[0].chunk.document_id, "doc-a")
        self.assertEqual(results[0].score, 0.75)

    async def test_keyword_search_uses_resolved_candidate_scope(self) -> None:
        chunks = CapturingChunkVectorStore([make_result("doc-a", "doc-a:chunk:0", 0.9)])
        document_projections = FakeDocumentProjectionRepository()
        document_port = FakeDocumentVectorStores(
            chunks=chunks,
            documents=FakeDocumentVectorStore(
                [DocumentRetrievalResult(document=make_document("doc-a"), score=0.7)]
            ),
        )

        await make_document_search_service(
            embeddings=FakeEmbeddingProvider(),
            documents=document_port,
            graph=FakeGraphStore(
                [DocumentRetrievalResult(document=make_document("doc-b"), score=0.6)]
            ),
            document_projections=document_projections,
            config=DocumentRetrievalConfig(top_k=1),
        ).search(
            RetrievalQuery(
                text="창업 관련 문서",
                request_context=RequestContext(
                    tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"
                ),
            )
        )

        self.assertEqual(document_projections.scopes[0].document_ids, ("doc-a", "doc-b"))

    async def test_document_and_chunk_dense_search_reuse_query_embedding(self) -> None:
        embeddings = FakeEmbeddingProvider()
        chunks = CapturingChunkVectorStore([make_result("doc-a", "doc-a:chunk:0", 0.9)])

        document_port = FakeDocumentVectorStores(
            chunks=chunks,
            documents=FakeDocumentVectorStore(
                [DocumentRetrievalResult(document=make_document("doc-a"), score=0.7)]
            ),
        )
        await make_document_search_service(
            embeddings=embeddings,
            documents=document_port,
            graph=FakeGraphStore([]),
            config=DocumentRetrievalConfig(top_k=1),
        ).search(
            RetrievalQuery(
                text="창업 관련 문서",
                request_context=RequestContext(
                    tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"
                ),
            )
        )

        self.assertEqual(embeddings.calls, 1)

    async def test_document_retrieval_rejects_embedding_count_mismatch(self) -> None:
        chunks = CapturingChunkVectorStore([])
        document_port = FakeDocumentVectorStores(chunks=chunks)

        with self.assertRaises(ProviderContractError):
            await make_document_search_service(
                embeddings=ShortEmbeddingProvider(),
                documents=document_port,
                graph=FakeGraphStore([]),
                config=DocumentRetrievalConfig(top_k=1),
            ).search(
                RetrievalQuery(
                    text="창업 관련 문서",
                    request_context=RequestContext(
                        tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"
                    ),
                )
            )


if __name__ == "__main__":
    unittest.main()
