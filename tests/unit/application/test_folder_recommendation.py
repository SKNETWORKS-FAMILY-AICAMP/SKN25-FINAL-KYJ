from __future__ import annotations

import unittest
from contextlib import asynccontextmanager
from datetime import datetime

from foldmind_ai_core.core.application.models.recommendation import FolderRecommendationSource
from foldmind_ai_core.core.application.errors import NoCandidatesError, ProviderContractError
from foldmind_ai_core.core.application.models.vector_projection import (
    DocumentVectorProjection,
    FolderVectorProjection,
)
from foldmind_ai_core.core.application.models.retrieval import FolderSearchQuery
from foldmind_ai_core.core.application.models.search import SearchScope
from foldmind_ai_core.core.application.services.recommendation.folder_recommendation_service import (  # noqa: E501
    FolderRecommendationService,
)
from foldmind_ai_core.core.application.services.retrieval.folder_retrieval_service import (
    FolderRetrievalService,
)
from foldmind_ai_core.core.application.services.retrieval.folder_search_service import (
    FolderSearchService,
)
from foldmind_ai_core.core.application.services.retrieval.ranking import (
    FolderRetrievalRanker,
)
from foldmind_ai_core.core.application.services.retrieval.scope_resolver import (
    RelationshipScopeResolver,
)
from foldmind_ai_core.core.application.models.retrieval import (
    DocumentRetrievalResult,
    FolderRetrievalResult,
    RetrievalResult,
    RetrievedDocument,
)
from foldmind_ai_core.core.domain.models.document_chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.document_sources import SourceDocument
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder
from foldmind_ai_core.shared.types import Vector
from foldmind_ai_core.shared.validation import InvalidInputError


class FakeEmbeddingProvider:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def embed_texts(self, texts: list[str]) -> list[Vector]:
        self.texts.extend(texts)
        return [[float(len(text))] for text in texts]


class ShortEmbeddingProvider:
    def embed_texts(self, texts: list[str]) -> list[Vector]:
        return []


class FakeDocumentVectorStore:
    def __init__(self) -> None:
        self.chunk_scope: SearchScope | None = None
        self.document_scope: SearchScope | None = None

    def replace_document_chunks(
        self,
        *,
        tenant: str,
        document_id: str,
        chunks: tuple[object, ...],
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
        self.chunk_scope = scope
        return [
            RetrievalResult(
                chunk=_chunk(document_id="doc-chunk"),
                score=0.3,
            )
        ]

    def search_documents(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[DocumentRetrievalResult]:
        self.document_scope = scope
        return [
            DocumentRetrievalResult(
                document=_retrieved_document(document_id="doc-doc"),
                score=0.4,
            )
        ]


class FailingDocumentVectorStore:
    def replace_document_chunks(
        self,
        *,
        tenant: str,
        document_id: str,
        chunks: tuple[object, ...],
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
        raise AssertionError("Document chunk search should be skipped.")

    def search_documents(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[DocumentRetrievalResult]:
        raise AssertionError("Document vector search should be skipped.")


class FakeFolderVectorStore:
    def __init__(self) -> None:
        self.scope: SearchScope | None = None
        self.scopes: list[SearchScope | None] = []

    def upsert_folder_vector(
        self,
        *,
        projection: FolderVectorProjection,
        vector: Vector,
    ) -> None:
        raise AssertionError("Folder vector writes are not expected in these tests.")

    def delete_folder_vector(self, *, tenant: str, folder_id: str) -> None:
        raise AssertionError("Folder vector deletes are not expected in these tests.")

    def search_folders(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[FolderRetrievalResult]:
        self.scope = scope
        self.scopes.append(scope)
        return [
            FolderRetrievalResult(
                folder=SourceFolder(
                    tenant=tenant,
                    folder_id="folder-b",
                    source_version="folder-v1",
                    name="folder-b",
                    created_at="2026-05-01T10:00:00+09:00",
                    updated_at="2026-05-02T11:00:00+09:00",
                ),
                score=0.2,
                reason="Folder metadata is semantically close.",
            )
        ]


class EmptyFolderVectorStore(FakeFolderVectorStore):
    def search_folders(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[FolderRetrievalResult]:
        self.scope = scope
        self.scopes.append(scope)
        return []


class FakeFolderSourceRepository:
    def __init__(
        self,
        *,
        name_matches: tuple[tuple[SourceFolder, float], ...] = (),
        description_matches: tuple[tuple[SourceFolder, float], ...] = (),
    ) -> None:
        self.name_matches = name_matches
        self.description_matches = description_matches
        self.name_scopes: list[tuple[str, ...]] = []
        self.description_scopes: list[tuple[str, ...]] = []

    async def search_names_by_keyword(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        folder_ids: tuple[str, ...],
        created_at: datetime | None,
        updated_at: datetime | None,
    ) -> tuple[tuple[SourceFolder, float], ...]:
        self.name_scopes.append(folder_ids)
        return self.name_matches[:top_k]

    async def search_descriptions_by_keyword(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        folder_ids: tuple[str, ...],
        created_at: datetime | None,
        updated_at: datetime | None,
    ) -> tuple[tuple[SourceFolder, float], ...]:
        self.description_scopes.append(folder_ids)
        return self.description_matches[:top_k]


class FakeRetrievalReadSession:
    def __init__(self, folder_sources: FakeFolderSourceRepository) -> None:
        self.folder_sources = folder_sources


class FakeRetrievalReadSessionProvider:
    def __init__(
        self,
        folder_sources: FakeFolderSourceRepository | None = None,
    ) -> None:
        self.folder_sources = folder_sources or FakeFolderSourceRepository()

    @asynccontextmanager
    async def session(self):
        yield FakeRetrievalReadSession(self.folder_sources)


class FakeGraphStore:
    def __init__(self) -> None:
        self.query_text: str | None = None
        self.scope: SearchScope | None = None

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
        self.query_text = query_text
        self.scope = scope
        return [
            DocumentRetrievalResult(
                document=_retrieved_document(document_id="doc-graph"),
                score=0.1,
            )
        ]

    def document_ids_for_scope(self, *, tenant: str, scope: SearchScope) -> tuple[str, ...]:
        return ("doc-doc", "doc-chunk", "doc-graph")

    def folders_for_documents(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
    ) -> dict[str, tuple[SourceFolder, ...]]:
        def folder(folder_id: str) -> SourceFolder:
            return SourceFolder(
                tenant=tenant,
                folder_id=folder_id,
                source_version=f"{folder_id}-v1",
                name=folder_id,
                created_at="2026-05-01T10:00:00+09:00",
                updated_at="2026-05-02T11:00:00+09:00",
            )

        return {
            "doc-doc": (folder("folder-a"), folder("folder-b")),
            "doc-chunk": (folder("folder-a"), folder("folder-c")),
            "doc-graph": (folder("folder-a"),),
        }


class EmptyRelationshipScopeGraphStore(FakeGraphStore):
    def document_ids_for_scope(self, *, tenant: str, scope: SearchScope) -> tuple[str, ...]:
        return ()

    def graph_search(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[DocumentRetrievalResult]:
        raise AssertionError("Graph search should be skipped.")

    def folders_for_documents(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
    ) -> dict[str, tuple[SourceFolder, ...]]:
        raise AssertionError("Document folder lookup should be skipped.")


class NoFolderCandidates:
    async def search(self, query: FolderSearchQuery) -> tuple[FolderRetrievalResult, ...]:
        return ()


class FolderRecommendationTests(unittest.IsolatedAsyncioTestCase):
    def test_folder_retrieval_service_rejects_malformed_numeric_options(self) -> None:
        with self.assertRaises(InvalidInputError):
            _folder_retrieval_service(top_k=True)
        with self.assertRaises(InvalidInputError):
            _folder_retrieval_service(top_k=0)
        with self.assertRaises(InvalidInputError):
            _folder_retrieval_service(candidate_multiplier=1.5)
        with self.assertRaises(InvalidInputError):
            _folder_retrieval_service(candidate_multiplier=-1)

    def test_folder_ranker_counts_each_document_folder_once(self) -> None:
        ranker = FolderRetrievalRanker(top_k=5)
        folder = SourceFolder(
            tenant="tenant-1",
            folder_id="folder-a",
            source_version="folder-v1",
            name="folder-a",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
        )

        ranker.add_document_signal(
            document_id="doc-1",
            score=0.4,
            reason="Similar document.",
        )
        ranker.add_document_folders({"doc-1": (folder, folder)})

        results = ranker.results()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].folder.folder_id, "folder-a")
        self.assertEqual(results[0].score, 0.4)

    def test_folder_ranker_ignores_non_finite_scores(self) -> None:
        ranker = FolderRetrievalRanker(top_k=5)
        valid_folder = SourceFolder(
            tenant="tenant-1",
            folder_id="folder-valid",
            source_version="folder-v1",
            name="folder-valid",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
        )
        invalid_folder = SourceFolder(
            tenant="tenant-1",
            folder_id="folder-invalid",
            source_version="folder-v1",
            name="folder-invalid",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
        )

        ranker.add_folder_score(
            folder=invalid_folder,
            score=float("nan"),
            reason="Invalid direct score.",
        )
        ranker.add_document_signal(
            document_id="doc-invalid",
            score=float("inf"),
            reason="Invalid document score.",
        )
        ranker.add_document_signal(
            document_id="doc-valid",
            score=0.3,
            reason="Valid document score.",
        )
        ranker.add_document_folders(
            {
                "doc-invalid": (invalid_folder,),
                "doc-valid": (valid_folder,),
            }
        )

        self.assertEqual(
            [result.folder.folder_id for result in ranker.results()],
            ["folder-valid"],
        )

    async def test_find_folders_aggregates_runtime_hits_by_folder_id(self) -> None:
        embeddings = FakeEmbeddingProvider()
        documents = FakeDocumentVectorStore()
        graph = FakeGraphStore()
        folders = FakeFolderVectorStore()
        service = FolderSearchService(
            retrieval=FolderRetrievalService(
                embeddings=embeddings,
                chunk_vectors=documents,
                document_vectors=documents,
                folder_vectors=folders,
                graph=graph,
                retrieval_reads=FakeRetrievalReadSessionProvider(),
                top_k=3,
            ),
            scope_resolver=RelationshipScopeResolver(graph=graph),
        )
        scope = SearchScope(document_type="document", folder_ids=("folder-startup",))
        query = FolderSearchQuery(
            text="창업과 관련된 폴더",
            tenant="tenant-1",
            scope=scope,
        )

        results = await service.search(query)

        self.assertEqual(
            [result.folder.folder_id for result in results],
            ["folder-a", "folder-b", "folder-c"],
        )
        self.assertEqual([round(result.score, 2) for result in results], [0.8, 0.4, 0.3])
        self.assertEqual(embeddings.texts, ["창업과 관련된 폴더"])
        self.assertEqual(
            documents.document_scope.document_ids,
            ("doc-doc", "doc-chunk", "doc-graph"),
        )
        self.assertEqual(
            documents.chunk_scope.document_ids,
            ("doc-doc", "doc-chunk", "doc-graph"),
        )
        self.assertEqual(folders.scopes, [])
        self.assertIs(graph.scope, scope)
        self.assertEqual(graph.query_text, "창업과 관련된 폴더")
        self.assertIn("Similar indexed document", results[0].reason)
        self.assertIn("Similar indexed chunk", results[0].reason)
        self.assertIn("Graph-related document", results[0].reason)

    async def test_find_folders_rejects_embedding_count_mismatch(self) -> None:
        with self.assertRaises(ProviderContractError):
            await FolderSearchService(
                retrieval=FolderRetrievalService(
                    embeddings=ShortEmbeddingProvider(),
                    chunk_vectors=FakeDocumentVectorStore(),
                    document_vectors=FakeDocumentVectorStore(),
                    folder_vectors=FakeFolderVectorStore(),
                    graph=FakeGraphStore(),
                    retrieval_reads=FakeRetrievalReadSessionProvider(),
                ),
                scope_resolver=RelationshipScopeResolver(graph=FakeGraphStore()),
            ).search(
                FolderSearchQuery(
                    text="창업과 관련된 폴더",
                    tenant="tenant-1",
                )
            )

    async def test_find_folders_keeps_folder_vector_scope_when_only_folder_ids_apply(
        self,
    ) -> None:
        documents = FakeDocumentVectorStore()
        graph = FakeGraphStore()
        folders = FakeFolderVectorStore()
        service = FolderSearchService(
            retrieval=FolderRetrievalService(
                embeddings=FakeEmbeddingProvider(),
                chunk_vectors=documents,
                document_vectors=documents,
                folder_vectors=folders,
                graph=graph,
                retrieval_reads=FakeRetrievalReadSessionProvider(),
                top_k=3,
            ),
            scope_resolver=RelationshipScopeResolver(graph=graph),
        )
        scope = SearchScope(folder_ids=("folder-b",))
        query = FolderSearchQuery(
            text="창업 폴더",
            tenant="tenant-1",
            scope=scope,
        )

        await service.search(query)

        self.assertEqual(len(folders.scopes), 1)
        self.assertEqual(folders.scope.folder_ids, ("folder-b",))

    async def test_find_folders_still_searches_scoped_folder_vectors_without_document_matches(
        self,
    ) -> None:
        folders = FakeFolderVectorStore()
        graph = EmptyRelationshipScopeGraphStore()
        service = FolderSearchService(
            retrieval=FolderRetrievalService(
                embeddings=FakeEmbeddingProvider(),
                chunk_vectors=FailingDocumentVectorStore(),
                document_vectors=FailingDocumentVectorStore(),
                folder_vectors=folders,
                graph=graph,
                retrieval_reads=FakeRetrievalReadSessionProvider(),
                top_k=3,
            ),
            scope_resolver=RelationshipScopeResolver(graph=graph),
        )

        results = await service.search(
            FolderSearchQuery(
                text="창업 폴더",
                tenant="tenant-1",
                scope=SearchScope(folder_ids=("folder-b",)),
            )
        )

        self.assertEqual([result.folder.folder_id for result in results], ["folder-b"])
        self.assertEqual(len(folders.scopes), 1)
        self.assertEqual(folders.scope.folder_ids, ("folder-b",))

    async def test_find_folders_returns_keyword_matches_without_folder_vectors(
        self,
    ) -> None:
        folder_sources = FakeFolderSourceRepository(
            name_matches=((_folder("folder-name"), 0.7),),
            description_matches=((_folder("folder-description"), 0.4),),
        )
        graph = EmptyRelationshipScopeGraphStore()
        service = FolderSearchService(
            retrieval=FolderRetrievalService(
                embeddings=FakeEmbeddingProvider(),
                chunk_vectors=FailingDocumentVectorStore(),
                document_vectors=FailingDocumentVectorStore(),
                folder_vectors=EmptyFolderVectorStore(),
                graph=graph,
                retrieval_reads=FakeRetrievalReadSessionProvider(folder_sources),
                top_k=3,
            ),
            scope_resolver=RelationshipScopeResolver(graph=graph),
        )

        results = await service.search(
            FolderSearchQuery(
                text="창업 폴더",
                tenant="tenant-1",
                scope=SearchScope(folder_ids=("folder-name", "folder-description")),
            )
        )

        self.assertEqual(
            [result.folder.folder_id for result in results],
            ["folder-name", "folder-description"],
        )
        self.assertIn("Folder name matches keyword.", results[0].reason)
        self.assertIn("Folder description matches keyword.", results[1].reason)

    async def test_find_folders_returns_empty_for_unresolved_tag_scope_without_vector_leak(
        self,
    ) -> None:
        folders = FakeFolderVectorStore()
        graph = EmptyRelationshipScopeGraphStore()
        service = FolderSearchService(
            retrieval=FolderRetrievalService(
                embeddings=FakeEmbeddingProvider(),
                chunk_vectors=FailingDocumentVectorStore(),
                document_vectors=FailingDocumentVectorStore(),
                folder_vectors=folders,
                graph=graph,
                retrieval_reads=FakeRetrievalReadSessionProvider(),
                top_k=3,
            ),
            scope_resolver=RelationshipScopeResolver(graph=graph),
        )

        results = await service.search(
            FolderSearchQuery(
                text="창업 폴더",
                tenant="tenant-1",
                scope=SearchScope(document_type="document", folder_ids=("folder-1",)),
            )
        )

        self.assertEqual(results, ())
        self.assertEqual(folders.scopes, [])

    async def test_recommend_folder_returns_folder_id_centered_result(self) -> None:
        graph = FakeGraphStore()
        result = await FolderRecommendationService(
            folder_search=FolderSearchService(
                retrieval=FolderRetrievalService(
                    embeddings=FakeEmbeddingProvider(),
                    chunk_vectors=FakeDocumentVectorStore(),
                    document_vectors=FakeDocumentVectorStore(),
                    folder_vectors=FakeFolderVectorStore(),
                    graph=graph,
                    retrieval_reads=FakeRetrievalReadSessionProvider(),
                    top_k=1,
                ),
                scope_resolver=RelationshipScopeResolver(graph=graph),
            )
        ).recommend(
            FolderRecommendationSource(
                document=SourceDocument(
                    tenant="tenant-1",
                    document_type="document",
                    document_id="doc-new",
                    source_version="v1",
                    created_at="2026-05-01T10:00:00+09:00",
                    updated_at="2026-05-02T11:00:00+09:00",
                    title="Startup memo",
                    body="창업 아이디어 정리",
                ),
            )
        )

        self.assertEqual(result.primary.folder_id, "folder-a")
        self.assertEqual(round(result.confidence, 2), 0.8)

    async def test_recommend_folder_raises_when_no_candidates_exist(self) -> None:
        with self.assertRaises(NoCandidatesError):
            service = FolderRecommendationService(
                folder_search=NoFolderCandidates()
            )
            await service.recommend(
                FolderRecommendationSource(
                    document=SourceDocument(
                        tenant="tenant-1",
                        document_type="document",
                        document_id="doc-new",
                        source_version="v1",
                        created_at="2026-05-01T10:00:00+09:00",
                        updated_at="2026-05-02T11:00:00+09:00",
                        title="Startup memo",
                        body="창업 아이디어 정리",
                    ),
                )
            )

    async def test_find_folders_returns_no_candidates_for_empty_source_document(
        self,
    ) -> None:
        embeddings = FakeEmbeddingProvider()
        graph = FakeGraphStore()
        service = FolderSearchService(
            retrieval=FolderRetrievalService(
                embeddings=embeddings,
                chunk_vectors=FakeDocumentVectorStore(),
                document_vectors=FakeDocumentVectorStore(),
                folder_vectors=FakeFolderVectorStore(),
                graph=graph,
                retrieval_reads=FakeRetrievalReadSessionProvider(),
            ),
            scope_resolver=RelationshipScopeResolver(graph=graph),
        )

        results = await service.search(
            FolderSearchQuery(
                tenant="tenant-1",
                text=" ",
            )
        )

        self.assertEqual(results, ())
        self.assertEqual(embeddings.texts, [])


def _chunk(*, document_id: str) -> DocumentChunk:
    return DocumentChunk(
        tenant="tenant-1",
        document_type="document",
        document_id=document_id,
        source_version="v1",
        document_index_input_digest="index-input-v1",
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        chunk_id=f"{document_id}:chunk:0",
        chunk_index=0,
        text="startup notes",
        start_offset=0,
        end_offset=len("startup notes"),
    )


def _retrieved_document(*, document_id: str) -> RetrievedDocument:
    return RetrievedDocument(
        tenant="tenant-1",
        document_type="document",
        document_id=document_id,
        source_version="v1",
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        snippet="startup notes",
    )


def _folder(folder_id: str) -> SourceFolder:
    return SourceFolder(
        tenant="tenant-1",
        folder_id=folder_id,
        source_version="folder-v1",
        name=folder_id,
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
    )


def _folder_retrieval_service(
    *,
    top_k: object = 5,
    candidate_multiplier: object = 4,
) -> FolderRetrievalService:
    return FolderRetrievalService(
        embeddings=FakeEmbeddingProvider(),
        chunk_vectors=FakeDocumentVectorStore(),
        document_vectors=FakeDocumentVectorStore(),
        folder_vectors=FakeFolderVectorStore(),
        graph=FakeGraphStore(),
        retrieval_reads=FakeRetrievalReadSessionProvider(),
        top_k=top_k,  # type: ignore[arg-type]
        candidate_multiplier=candidate_multiplier,  # type: ignore[arg-type]
    )


if __name__ == "__main__":
    unittest.main()
