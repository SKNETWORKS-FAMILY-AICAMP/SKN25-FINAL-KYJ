from __future__ import annotations

import unittest

from foldmind_ai_core.core.application.errors import ProviderContractError
from foldmind_ai_core.core.application.projections.vector import DocumentVectorProjection
from foldmind_ai_core.core.application.services.document_retrieval_policy import (
    DocumentRetrievalConfig,
    rank_document_candidates,
)
from foldmind_ai_core.core.application.services.document_retrieval_service import (
    DocumentRetrievalService,
)
from foldmind_ai_core.core.application.services.relationship_scope_resolver import (
    RelationshipScopeResolver,
)
from foldmind_ai_core.core.application.use_cases.retrieval.find_documents import FindDocumentsUseCase
from foldmind_ai_core.core.application.queries.retrieval import (
    RequestContext,
    RetrievalQuery,
    SearchScope,
    SearchSort,
    TimestampRange,
)
from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.retrieval.results import (
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
        document_id: str,
    ) -> None:
        raise AssertionError("Document chunk deletes are not expected in these tests.")

    def delete_document_vector(
        self,
        *,
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


class FakeKeywordSearchStore:
    def __init__(self, results: list[RetrievalResult]) -> None:
        self.results = results
        self.scopes: list[SearchScope | None] = []

    def search_chunks(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[RetrievalResult]:
        self.scopes.append(scope)
        return self.results[:top_k]


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
        document_id: str,
    ) -> None:
        raise AssertionError("Graph document deletes are not expected in these tests.")

    def delete_folder(self, *, folder_id: str) -> None:
        raise AssertionError("Graph folder deletes are not expected in these tests.")

    def delete_folder_signals(self, *, folder_id: str) -> None:
        raise AssertionError("Folder signal deletes are not expected in these tests.")

    def delete_stale_folder_signals(
        self,
        *,
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


class FakeRelevanceValidator:
    def __init__(self, allowed_chunk_ids: set[str]) -> None:
        self.allowed_chunk_ids = allowed_chunk_ids

    def filter(
        self,
        *,
        query: RetrievalQuery,
        results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        return [
            result
            for result in results
            if result.chunk.chunk_id in self.allowed_chunk_ids
        ]


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
            chunking_version="chunking-test-v1",
            text=text,
            text_hash="hash-1",
            start_offset=0,
            end_offset=len(text),
            embedding_model="test-embedding",
            embedding_version="test-v1",
            index_schema_version="schema-v1",
        ),
        score=score,
    )


def make_find_documents_use_case(
    *,
    embeddings: FakeEmbeddingProvider,
    documents: FakeDocumentVectorStores,
    graph: FakeGraphStore,
    result_filter: FakeRelevanceValidator | None = None,
    keyword_chunks: FakeKeywordSearchStore | None = None,
    config: DocumentRetrievalConfig,
) -> FindDocumentsUseCase:
    return FindDocumentsUseCase(
        retrieval=DocumentRetrievalService(
            embeddings=embeddings,
            chunk_vectors=documents,
            document_vectors=documents,
            graph=graph,
            keyword_chunks=keyword_chunks,
            config=config,
        ),
        scope_resolver=RelationshipScopeResolver(graph=graph),
        result_filter=result_filter,
    )


class DocumentRetrievalTests(unittest.TestCase):
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
        ranked = rank_document_candidates(
            document_results=[
                DocumentRetrievalResult(document=make_document("doc-a"), score=0.4),
                DocumentRetrievalResult(document=make_document("doc-a"), score=0.3),
                DocumentRetrievalResult(document=make_document("doc-b"), score=0.9),
            ],
            graph_results=[],
            both_sources_bonus=0.15,
        )

        self.assertEqual([result.document.document_id for result in ranked], ["doc-b", "doc-a"])
        self.assertEqual(ranked[1].score, 0.4)

    def test_document_candidates_ignore_blank_ids_and_non_finite_scores(self) -> None:
        ranked = rank_document_candidates(
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
            both_sources_bonus=0.15,
        )

        self.assertEqual(
            [result.document.document_id for result in ranked],
            ["doc-valid"],
        )

    def test_chunk_results_ignore_blank_ids_and_non_finite_scores(self) -> None:
        chunks = CapturingChunkVectorStore(
            [
                make_result(" ", "blank:chunk:0", 0.9),
                make_result("doc-invalid", "doc-invalid:chunk:0", float("nan")),
                make_result("doc-valid", "doc-valid:chunk:0", 0.7),
            ]
        )
        document_port = FakeDocumentVectorStores(chunks=chunks)

        results = make_find_documents_use_case(
            embeddings=FakeEmbeddingProvider(),
            documents=document_port,
            graph=FakeGraphStore([]),
            config=DocumentRetrievalConfig(top_k=3),
        ).execute(
            RetrievalQuery(text="창업 관련 문서", request_context=RequestContext(tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"))
        ).results

        self.assertEqual(
            [result.document_id for result in results],
            ["doc-valid"],
        )

    def test_document_candidates_receive_cross_source_bonus_once(self) -> None:
        ranked = rank_document_candidates(
            document_results=[
                DocumentRetrievalResult(document=make_document("doc-a"), score=0.5),
            ],
            graph_results=[
                DocumentRetrievalResult(document=make_document("doc-a"), score=0.7),
                DocumentRetrievalResult(document=make_document("doc-a"), score=0.6),
            ],
            both_sources_bonus=0.15,
        )

        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0].document.document_id, "doc-a")
        self.assertEqual(ranked[0].score, 0.85)

    def test_qdrant_documents_and_graph_candidates_constrain_chunk_search(self) -> None:
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
        results = make_find_documents_use_case(
            embeddings=FakeEmbeddingProvider(),
            documents=document_port,
            graph=FakeGraphStore(
                [DocumentRetrievalResult(document=make_document("doc-b"), score=0.6)]
            ),
            config=DocumentRetrievalConfig(top_k=2),
        ).execute(
            RetrievalQuery(text="창업 관련 문서", request_context=RequestContext(tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"))
        ).results

        self.assertEqual([result.document_id for result in results], ["doc-a", "doc-b"])
        self.assertEqual(chunks.scopes[0].document_ids, ("doc-a", "doc-b"))

    def test_explicit_document_scope_is_not_replaced_by_candidates(self) -> None:
        chunks = CapturingChunkVectorStore(
            [make_result("doc-a", "doc-a:chunk:0", 0.9)]
        )
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

        make_find_documents_use_case(
            embeddings=FakeEmbeddingProvider(),
            documents=document_port,
            graph=FakeGraphStore(
                [DocumentRetrievalResult(document=make_document("doc-c"), score=0.6)]
            ),
            config=DocumentRetrievalConfig(top_k=1),
        ).execute(
            RetrievalQuery(
                text="창업 관련 문서",
                request_context=RequestContext(tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"),
                scope=SearchScope(document_id="doc-a"),
            )
        )

        self.assertEqual(chunks.scopes[0].document_id, "doc-a")
        self.assertEqual(chunks.scopes[0].document_ids, ())
        self.assertIsNone(chunks.scopes[0].document_type)

    def test_mixed_document_type_candidates_do_not_force_first_type(self) -> None:
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

        make_find_documents_use_case(
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
        ).execute(
            RetrievalQuery(text="창업 관련 문서", request_context=RequestContext(tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"))
        )

        self.assertIsNone(chunks.scopes[0].document_type)
        self.assertEqual(chunks.scopes[0].document_ids, ("doc-a", "note-b"))

    def test_relationship_scope_uses_resolved_document_set_without_readding_anchor(
        self,
    ) -> None:
        chunks = CapturingChunkVectorStore(
            [make_result("doc-b", "doc-b:chunk:0", 0.9)]
        )
        document_port = FakeDocumentVectorStores(chunks=chunks)

        make_find_documents_use_case(
            embeddings=FakeEmbeddingProvider(),
            documents=document_port,
            graph=FakeGraphStore([], scoped_document_ids=("doc-b",)),
            config=DocumentRetrievalConfig(top_k=1),
        ).execute(
            RetrievalQuery(
                text="창업 관련 문서",
                request_context=RequestContext(tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"),
                scope=SearchScope(
                    document_id="doc-a",
                    document_ids=("doc-b",),
                    folder_ids=("folder-1",),
                    created_at=TimestampRange(gte="2026-05-01T00:00:00+09:00"),
                    sort=SearchSort(field="created_at", direction="desc"),
                ),
            )
        )

        self.assertIsNone(chunks.scopes[0].document_id)
        self.assertEqual(chunks.scopes[0].document_ids, ("doc-b",))
        self.assertEqual(chunks.scopes[0].folder_ids, ())
        self.assertEqual(chunks.scopes[0].created_at.gte, "2026-05-01T00:00:00+09:00")
        self.assertEqual(chunks.scopes[0].sort.field, "created_at")
        self.assertEqual(chunks.scopes[0].sort.direction, "desc")

    def test_relevance_filter_removes_unrelated_chunks_before_summary(self) -> None:
        document_port = FakeDocumentVectorStores(
            chunks=CapturingChunkVectorStore(
                [
                    make_result("doc-a", "doc-a:chunk:0", 0.9),
                    make_result("doc-b", "doc-b:chunk:0", 0.8),
                ]
            ),
        )
        results = make_find_documents_use_case(
            embeddings=FakeEmbeddingProvider(),
            documents=document_port,
            graph=FakeGraphStore([]),
            result_filter=FakeRelevanceValidator({"doc-b:chunk:0"}),
            config=DocumentRetrievalConfig(top_k=2),
        ).execute(
            RetrievalQuery(text="창업 관련 문서", request_context=RequestContext(tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"))
        ).results

        self.assertEqual([result.chunk_id for result in results], ["doc-b:chunk:0"])

    def test_keyword_results_are_merged_with_dense_chunk_results(self) -> None:
        document_port = FakeDocumentVectorStores(
            chunks=CapturingChunkVectorStore(
                [make_result("doc-a", "doc-a:chunk:0", 0.9)]
            ),
        )
        keyword_chunks = FakeKeywordSearchStore(
            [make_result("doc-b", "doc-b:chunk:0", 0.8)]
        )

        results = make_find_documents_use_case(
            embeddings=FakeEmbeddingProvider(),
            documents=document_port,
            graph=FakeGraphStore([]),
            keyword_chunks=keyword_chunks,
            config=DocumentRetrievalConfig(top_k=2, keyword_top_k=1),
        ).execute(
            RetrievalQuery(text="창업 관련 문서", request_context=RequestContext(tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"))
        ).results

        self.assertEqual(
            {result.document_id for result in results},
            {"doc-a", "doc-b"},
        )

    def test_keyword_search_uses_resolved_candidate_scope(self) -> None:
        chunks = CapturingChunkVectorStore(
            [make_result("doc-a", "doc-a:chunk:0", 0.9)]
        )
        keyword_chunks = FakeKeywordSearchStore([])
        document_port = FakeDocumentVectorStores(
            chunks=chunks,
            documents=FakeDocumentVectorStore(
                [DocumentRetrievalResult(document=make_document("doc-a"), score=0.7)]
            ),
        )

        make_find_documents_use_case(
            embeddings=FakeEmbeddingProvider(),
            documents=document_port,
            graph=FakeGraphStore(
                [DocumentRetrievalResult(document=make_document("doc-b"), score=0.6)]
            ),
            keyword_chunks=keyword_chunks,
            config=DocumentRetrievalConfig(top_k=1),
        ).execute(
            RetrievalQuery(text="창업 관련 문서", request_context=RequestContext(tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"))
        )

        self.assertEqual(keyword_chunks.scopes[0].document_ids, ("doc-a", "doc-b"))

    def test_document_and_chunk_dense_search_reuse_query_embedding(self) -> None:
        embeddings = FakeEmbeddingProvider()
        chunks = CapturingChunkVectorStore([make_result("doc-a", "doc-a:chunk:0", 0.9)])

        document_port = FakeDocumentVectorStores(
            chunks=chunks,
            documents=FakeDocumentVectorStore(
                [DocumentRetrievalResult(document=make_document("doc-a"), score=0.7)]
            ),
        )
        make_find_documents_use_case(
            embeddings=embeddings,
            documents=document_port,
            graph=FakeGraphStore([]),
            config=DocumentRetrievalConfig(top_k=1),
        ).execute(
            RetrievalQuery(text="창업 관련 문서", request_context=RequestContext(tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"))
        )

        self.assertEqual(embeddings.calls, 1)

    def test_document_retrieval_rejects_embedding_count_mismatch(self) -> None:
        chunks = CapturingChunkVectorStore([])
        document_port = FakeDocumentVectorStores(chunks=chunks)

        with self.assertRaises(ProviderContractError):
            make_find_documents_use_case(
                embeddings=ShortEmbeddingProvider(),
                documents=document_port,
                graph=FakeGraphStore([]),
                config=DocumentRetrievalConfig(top_k=1),
            ).execute(
                RetrievalQuery(
                    text="창업 관련 문서",
                    request_context=RequestContext(tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"),
                )
            )


if __name__ == "__main__":
    unittest.main()
