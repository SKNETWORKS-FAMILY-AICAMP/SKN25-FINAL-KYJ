from __future__ import annotations

import unittest

from foldmind_ai_core.core.application.commands.recommendation import RecommendFolderCommand
from foldmind_ai_core.core.application.errors import NoCandidatesError, ProviderContractError
from foldmind_ai_core.core.application.projections.vector import (
    DocumentVectorProjection,
    FolderVectorProjection,
)
from foldmind_ai_core.core.application.services.folder_retrieval_ranker import (
    FolderRetrievalRanker,
)
from foldmind_ai_core.core.application.services.folder_retrieval_service import (
    FolderRetrievalService,
)
from foldmind_ai_core.core.application.services.relationship_scope_resolver import (
    RelationshipScopeResolver,
)
from foldmind_ai_core.core.application.use_cases.recommendation.find_folders import FindFoldersUseCase
from foldmind_ai_core.core.application.use_cases.recommendation.recommend_folder import (
    RecommendFolderUseCase,
)
from foldmind_ai_core.core.application.queries.retrieval import (
    FolderSearchQuery,
    SearchScope,
)
from foldmind_ai_core.core.application.results.retrieval import SearchFoldersResult
from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.retrieval.results import (
    DocumentRetrievalResult,
    FolderRetrievalResult,
    RetrievalResult,
    RetrievedDocument,
    RetrievedFolder,
)
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

    def delete_folder_vector(self, *, folder_id: str) -> None:
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
                folder=RetrievedFolder(
                    tenant=tenant,
                    folder_id="folder-b",
                    source_version="folder-v1",
                    created_at="2026-05-01T10:00:00+09:00",
                    updated_at="2026-05-02T11:00:00+09:00",
                ),
                score=0.2,
                reason="Folder metadata is semantically close.",
            )
        ]


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

    def replace_folder_hierarchy(self, projection: object) -> None:
        raise AssertionError("Folder hierarchy writes are not expected in these tests.")

    def replace_folder_projection(self, *, relationships: object, signals: object) -> None:
        raise AssertionError("Folder projection writes are not expected in these tests.")

    def delete_document(
        self,
        *,
        document_id: str,
    ) -> None:
        raise AssertionError("Graph document deletes are not expected in these tests.")

    def delete_folder(self, *, folder_id: str) -> None:
        raise AssertionError("Graph folder deletes are not expected in these tests.")

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
    ) -> dict[str, tuple[RetrievedFolder, ...]]:
        def folder(folder_id: str) -> RetrievedFolder:
            return RetrievedFolder(
                tenant=tenant,
                folder_id=folder_id,
                source_version=f"{folder_id}-v1",
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
    ) -> dict[str, tuple[RetrievedFolder, ...]]:
        raise AssertionError("Document folder lookup should be skipped.")


class NoFolderCandidates:
    def execute(self, query: FolderSearchQuery) -> SearchFoldersResult:
        return SearchFoldersResult(results=())


class FolderRecommendationTests(unittest.TestCase):
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
        folder = RetrievedFolder(
            tenant="tenant-1",
            folder_id="folder-a",
            source_version="folder-v1",
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
        valid_folder = RetrievedFolder(
            tenant="tenant-1",
            folder_id="folder-valid",
            source_version="folder-v1",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
        )
        invalid_folder = RetrievedFolder(
            tenant="tenant-1",
            folder_id="folder-invalid",
            source_version="folder-v1",
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

    def test_find_folders_aggregates_runtime_hits_by_folder_id(self) -> None:
        embeddings = FakeEmbeddingProvider()
        documents = FakeDocumentVectorStore()
        graph = FakeGraphStore()
        folders = FakeFolderVectorStore()
        use_case = FindFoldersUseCase(
            retrieval=FolderRetrievalService(
                embeddings=embeddings,
                chunk_vectors=documents,
                document_vectors=documents,
                folder_vectors=folders,
                graph=graph,
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

        results = use_case.execute(query).results

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

    def test_find_folders_rejects_embedding_count_mismatch(self) -> None:
        with self.assertRaises(ProviderContractError):
            FindFoldersUseCase(
                retrieval=FolderRetrievalService(
                    embeddings=ShortEmbeddingProvider(),
                    chunk_vectors=FakeDocumentVectorStore(),
                    document_vectors=FakeDocumentVectorStore(),
                    folder_vectors=FakeFolderVectorStore(),
                    graph=FakeGraphStore(),
                ),
                scope_resolver=RelationshipScopeResolver(graph=FakeGraphStore()),
            ).execute(
                FolderSearchQuery(
                    text="창업과 관련된 폴더",
                    tenant="tenant-1",
                )
            )

    def test_find_folders_keeps_folder_vector_scope_when_only_folder_ids_apply(
        self,
    ) -> None:
        documents = FakeDocumentVectorStore()
        graph = FakeGraphStore()
        folders = FakeFolderVectorStore()
        use_case = FindFoldersUseCase(
            retrieval=FolderRetrievalService(
                embeddings=FakeEmbeddingProvider(),
                chunk_vectors=documents,
                document_vectors=documents,
                folder_vectors=folders,
                graph=graph,
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

        use_case.execute(query)

        self.assertEqual(len(folders.scopes), 1)
        self.assertEqual(folders.scope.folder_ids, ("folder-b",))

    def test_find_folders_still_searches_scoped_folder_vectors_without_document_matches(
        self,
    ) -> None:
        folders = FakeFolderVectorStore()
        graph = EmptyRelationshipScopeGraphStore()
        use_case = FindFoldersUseCase(
            retrieval=FolderRetrievalService(
                embeddings=FakeEmbeddingProvider(),
                chunk_vectors=FailingDocumentVectorStore(),
                document_vectors=FailingDocumentVectorStore(),
                folder_vectors=folders,
                graph=graph,
                top_k=3,
            ),
            scope_resolver=RelationshipScopeResolver(graph=graph),
        )

        results = use_case.execute(
            FolderSearchQuery(
                text="창업 폴더",
                tenant="tenant-1",
                scope=SearchScope(folder_ids=("folder-b",)),
            )
        ).results

        self.assertEqual([result.folder.folder_id for result in results], ["folder-b"])
        self.assertEqual(len(folders.scopes), 1)
        self.assertEqual(folders.scope.folder_ids, ("folder-b",))

    def test_find_folders_returns_empty_for_unresolved_tag_scope_without_vector_leak(
        self,
    ) -> None:
        folders = FakeFolderVectorStore()
        graph = EmptyRelationshipScopeGraphStore()
        use_case = FindFoldersUseCase(
            retrieval=FolderRetrievalService(
                embeddings=FakeEmbeddingProvider(),
                chunk_vectors=FailingDocumentVectorStore(),
                document_vectors=FailingDocumentVectorStore(),
                folder_vectors=folders,
                graph=graph,
                top_k=3,
            ),
            scope_resolver=RelationshipScopeResolver(graph=graph),
        )

        results = use_case.execute(
            FolderSearchQuery(
                text="창업 폴더",
                tenant="tenant-1",
                scope=SearchScope(document_type="document", folder_ids=("folder-1",)),
            )
        )

        self.assertEqual(results.results, ())
        self.assertEqual(folders.scopes, [])

    def test_recommend_folder_returns_folder_id_centered_result(self) -> None:
        graph = FakeGraphStore()
        result = RecommendFolderUseCase(
            find_folders=FindFoldersUseCase(
                retrieval=FolderRetrievalService(
                    embeddings=FakeEmbeddingProvider(),
                    chunk_vectors=FakeDocumentVectorStore(),
                    document_vectors=FakeDocumentVectorStore(),
                    folder_vectors=FakeFolderVectorStore(),
                    graph=graph,
                    top_k=1,
                ),
                scope_resolver=RelationshipScopeResolver(graph=graph),
            )
        ).execute(
            RecommendFolderCommand(
                tenant="tenant-1",
                document_type="document",
                document_id="doc-new",
                source_version="v1",
                created_at="2026-05-01T10:00:00+09:00",
                updated_at="2026-05-02T11:00:00+09:00",
                title="Startup memo",
                body="창업 아이디어 정리",
            )
        )

        self.assertEqual(result.primary.folder_id, "folder-a")
        self.assertEqual(round(result.confidence, 2), 0.8)

    def test_recommend_folder_raises_when_no_candidates_exist(self) -> None:
        with self.assertRaises(NoCandidatesError):
            RecommendFolderUseCase(find_folders=NoFolderCandidates()).execute(
                RecommendFolderCommand(
                    tenant="tenant-1",
                    document_type="document",
                    document_id="doc-new",
                    source_version="v1",
                    created_at="2026-05-01T10:00:00+09:00",
                    updated_at="2026-05-02T11:00:00+09:00",
                    title="Startup memo",
                    body="창업 아이디어 정리",
                )
            )

    def test_find_folders_returns_no_candidates_for_empty_source_document(self) -> None:
        embeddings = FakeEmbeddingProvider()
        graph = FakeGraphStore()
        use_case = FindFoldersUseCase(
            retrieval=FolderRetrievalService(
                embeddings=embeddings,
                chunk_vectors=FakeDocumentVectorStore(),
                document_vectors=FakeDocumentVectorStore(),
                folder_vectors=FakeFolderVectorStore(),
                graph=graph,
            ),
            scope_resolver=RelationshipScopeResolver(graph=graph),
        )

        results = use_case.execute(
            FolderSearchQuery(
                tenant="tenant-1",
                text=" ",
            )
        )

        self.assertEqual(results.results, ())
        self.assertEqual(embeddings.texts, [])


def _chunk(*, document_id: str) -> DocumentChunk:
    return DocumentChunk(
        tenant="tenant-1",
        document_type="document",
        document_id=document_id,
        source_version="v1",
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        chunk_id=f"{document_id}:chunk:0",
        chunk_index=0,
        chunking_version="chunking-test-v1",
        text="startup notes",
        text_hash="hash-1",
        start_offset=0,
        end_offset=len("startup notes"),
        embedding_model="test-embedding",
        embedding_version="test-v1",
        index_schema_version="schema-v1",
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
        top_k=top_k,  # type: ignore[arg-type]
        candidate_multiplier=candidate_multiplier,  # type: ignore[arg-type]
    )


if __name__ == "__main__":
    unittest.main()
