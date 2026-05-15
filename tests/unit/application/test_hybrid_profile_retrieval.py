from __future__ import annotations

import unittest

from foldmind_ai_core.application.services.document_retrieval_policy import (
    HybridSearchConfig,
    SearchMode,
)
from foldmind_ai_core.application.services.document_retrieval_service import (
    DocumentRetrievalService,
)
from foldmind_ai_core.application.services.relationship_scope_resolver import (
    RelationshipScopeResolver,
)
from foldmind_ai_core.application.use_cases.retrieval.find_documents import FindDocumentsUseCase
from foldmind_ai_core.domain.indexing.chunks import DocumentChunk
from foldmind_ai_core.domain.reference.documents import (
    DocumentVectorProjection,
)
from foldmind_ai_core.domain.retrieval.queries import AIQuery, RequestContext, SearchScope
from foldmind_ai_core.domain.retrieval.results import (
    DocumentRetrievalResult,
    RetrievalResult,
    RetrievedDocument,
)
from foldmind_ai_core.shared.types import Vector


class FakeEmbeddingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def embed_texts(self, texts: list[str]) -> list[Vector]:
        self.calls += 1
        return [[float(len(text))] for text in texts]


class CapturingChunkVectorRepository:
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


class FakeDocumentVectorRepository:
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


class FakeDocumentRepositories:
    def __init__(
        self,
        *,
        chunks: CapturingChunkVectorRepository,
        documents: FakeDocumentVectorRepository | None = None,
    ) -> None:
        self.chunks = chunks
        self.documents = documents

    def replace_document_chunks(
        self,
        *,
        document_id: str,
        chunks: tuple[DocumentChunk, ...],
        vectors: tuple[Vector, ...],
    ) -> None:
        return None

    def upsert_document_vector(
        self,
        *,
        projection: DocumentVectorProjection,
        vector: Vector,
    ) -> None:
        return None

    def delete_document_chunks(
        self,
        *,
        document_id: str,
    ) -> None:
        return None

    def delete_document_vector(
        self,
        *,
        document_id: str,
    ) -> None:
        return None

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


class FakeGraphRepository:
    def __init__(self, results: list[DocumentRetrievalResult]) -> None:
        self.results = results

    def replace_document_projection(
        self,
        *,
        relationships: object,
        concepts: object,
    ) -> None:
        pass

    def replace_folder_hierarchy(self, projection: object) -> None:
        pass

    def upsert_tag(self, projection: object) -> None:
        pass

    def delete_document(self, *, document_id: str) -> None:
        pass

    def delete_folder(self, *, folder_id: str) -> None:
        pass

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
        query: AIQuery,
        results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        return [
            result
            for result in results
            if result.chunk.chunk_id in self.allowed_chunk_ids
        ]


def make_document(document_id: str, score_text: str = "") -> RetrievedDocument:
    return RetrievedDocument(
        tenant="tenant-1",
        document_type="document",
        document_id=document_id,
        source_version="v1",
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
    documents: FakeDocumentRepositories,
    graph: FakeGraphRepository,
    result_filter: FakeRelevanceValidator | None = None,
    config: HybridSearchConfig,
) -> FindDocumentsUseCase:
    return FindDocumentsUseCase(
        retrieval=DocumentRetrievalService(
            embeddings=embeddings,
            chunk_vectors=documents,
            document_vectors=documents,
            graph=graph,
            config=config,
        ),
        scope_resolver=RelationshipScopeResolver(graph=graph),
        result_filter=result_filter,
    )


class HybridProfileRetrievalTests(unittest.TestCase):
    def test_qdrant_documents_and_graph_candidates_constrain_chunk_search(self) -> None:
        chunks = CapturingChunkVectorRepository(
            [
                make_result("doc-a", "doc-a:chunk:0", 0.9),
                make_result("doc-b", "doc-b:chunk:0", 0.8),
            ]
        )

        document_port = FakeDocumentRepositories(
            chunks=chunks,
            documents=FakeDocumentVectorRepository(
                [DocumentRetrievalResult(document=make_document("doc-a"), score=0.7)]
            ),
        )
        results = make_find_documents_use_case(
            embeddings=FakeEmbeddingProvider(),
            documents=document_port,
            graph=FakeGraphRepository(
                [DocumentRetrievalResult(document=make_document("doc-b"), score=0.6)]
            ),
            config=HybridSearchConfig(mode=SearchMode.DENSE, top_k=2),
        ).execute(
            AIQuery(text="창업 관련 문서", request_context=RequestContext(tenant="tenant-1"))
        )

        self.assertEqual([result.chunk.document_id for result in results], ["doc-a", "doc-b"])
        self.assertEqual(chunks.scopes[0].document_ids, ("doc-a", "doc-b"))

    def test_relevance_validator_filters_chunk_results_before_summary(self) -> None:
        document_port = FakeDocumentRepositories(
            chunks=CapturingChunkVectorRepository(
                [
                    make_result("doc-a", "doc-a:chunk:0", 0.9),
                    make_result("doc-b", "doc-b:chunk:0", 0.8),
                ]
            ),
        )
        results = make_find_documents_use_case(
            embeddings=FakeEmbeddingProvider(),
            documents=document_port,
            graph=FakeGraphRepository([]),
            result_filter=FakeRelevanceValidator({"doc-b:chunk:0"}),
            config=HybridSearchConfig(mode=SearchMode.DENSE, top_k=2),
        ).execute(
            AIQuery(text="창업 관련 문서", request_context=RequestContext(tenant="tenant-1"))
        )

        self.assertEqual([result.chunk.chunk_id for result in results], ["doc-b:chunk:0"])

    def test_document_and_chunk_dense_search_reuse_query_embedding(self) -> None:
        embeddings = FakeEmbeddingProvider()
        chunks = CapturingChunkVectorRepository([make_result("doc-a", "doc-a:chunk:0", 0.9)])

        document_port = FakeDocumentRepositories(
            chunks=chunks,
            documents=FakeDocumentVectorRepository(
                [DocumentRetrievalResult(document=make_document("doc-a"), score=0.7)]
            ),
        )
        make_find_documents_use_case(
            embeddings=embeddings,
            documents=document_port,
            graph=FakeGraphRepository([]),
            config=HybridSearchConfig(mode=SearchMode.DENSE, top_k=1),
        ).execute(
            AIQuery(text="창업 관련 문서", request_context=RequestContext(tenant="tenant-1"))
        )

        self.assertEqual(embeddings.calls, 1)


if __name__ == "__main__":
    unittest.main()
