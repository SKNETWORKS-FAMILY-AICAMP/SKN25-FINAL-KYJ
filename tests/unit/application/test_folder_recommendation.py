from __future__ import annotations

import unittest

from foldmind_ai_core.application.services.folder_retrieval_service import (
    FolderRetrievalService,
)
from foldmind_ai_core.application.services.relationship_scope_resolver import (
    RelationshipScopeResolver,
)
from foldmind_ai_core.application.use_cases.recommendation.find_folders import FindFoldersUseCase
from foldmind_ai_core.application.use_cases.recommendation.recommend_folder import (
    RecommendFolderUseCase,
)
from foldmind_ai_core.domain.indexing.chunks import DocumentChunk
from foldmind_ai_core.domain.reference.documents import (
    DocumentVectorProjection,
    SourceDocument,
)
from foldmind_ai_core.domain.reference.folders import FolderVectorProjection
from foldmind_ai_core.domain.retrieval.queries import AIQuery, RequestContext, SearchScope
from foldmind_ai_core.domain.retrieval.results import (
    DocumentRetrievalResult,
    FolderRetrievalResult,
    RetrievalResult,
    RetrievedDocument,
    RetrievedFolder,
)
from foldmind_ai_core.shared.types import Vector


class FakeEmbeddingProvider:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def embed_texts(self, texts: list[str]) -> list[Vector]:
        self.texts.extend(texts)
        return [[float(len(text))] for text in texts]


class FakeDocumentVectorRepository:
    def __init__(self) -> None:
        self.chunk_scope: SearchScope | None = None
        self.document_scope: SearchScope | None = None

    def replace_document_chunks(
        self,
        *,
        document_id: str,
        chunks: tuple[DocumentChunk, ...],
        vectors: tuple[Vector, ...],
    ) -> None:
        pass

    def upsert_document_vector(
        self,
        *,
        projection: DocumentVectorProjection,
        vector: Vector,
    ) -> None:
        pass

    def delete_document_chunks(
        self,
        *,
        document_id: str,
    ) -> None:
        pass

    def delete_document_vector(
        self,
        *,
        document_id: str,
    ) -> None:
        pass

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


class FakeFolderVectorRepository:
    def __init__(self) -> None:
        self.scope: SearchScope | None = None

    def upsert_folder_vector(
        self,
        *,
        projection: FolderVectorProjection,
        vector: Vector,
    ) -> None:
        pass

    def delete_folder_vector(self, *, folder_id: str) -> None:
        pass

    def search_folders(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[FolderRetrievalResult]:
        self.scope = scope
        return [
            FolderRetrievalResult(
                folder=RetrievedFolder(
                    tenant=tenant,
                    folder_id="folder-b",
                    source_version="folder-v1",
                ),
                score=0.2,
                reason="Folder metadata is semantically close.",
            )
        ]


class FakeGraphRepository:
    def __init__(self) -> None:
        self.query_text: str | None = None
        self.scope: SearchScope | None = None

    def replace_document_relationships(self, projection: object) -> None:
        pass

    def replace_document_concepts(self, projection: object) -> None:
        pass

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


class FolderRecommendationTests(unittest.TestCase):
    def test_find_folders_aggregates_runtime_hits_by_folder_id(self) -> None:
        embeddings = FakeEmbeddingProvider()
        documents = FakeDocumentVectorRepository()
        graph = FakeGraphRepository()
        folders = FakeFolderVectorRepository()
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
        scope = SearchScope(tag_ids=("startup",))
        query = AIQuery(
            text="창업과 관련된 폴더",
            request_context=RequestContext(tenant="tenant-1"),
            scope=scope,
        )

        results = use_case.execute(query)

        self.assertEqual(
            [result.folder.folder_id for result in results],
            ["folder-a", "folder-b", "folder-c"],
        )
        self.assertEqual([round(result.score, 2) for result in results], [0.8, 0.6, 0.3])
        self.assertEqual(embeddings.texts, ["창업과 관련된 폴더"])
        self.assertEqual(
            documents.document_scope.document_ids,
            ("doc-doc", "doc-chunk", "doc-graph"),
        )
        self.assertEqual(
            documents.chunk_scope.document_ids,
            ("doc-doc", "doc-chunk", "doc-graph"),
        )
        self.assertEqual(documents.document_scope.tag_ids, ())
        self.assertEqual(documents.chunk_scope.tag_ids, ())
        self.assertIs(folders.scope, scope)
        self.assertIs(graph.scope, scope)
        self.assertEqual(graph.query_text, "창업과 관련된 폴더")
        self.assertIn("Similar indexed document", results[0].reason)
        self.assertIn("Similar indexed chunk", results[0].reason)
        self.assertIn("Graph-related document", results[0].reason)

    def test_recommend_folder_returns_folder_id_centered_result(self) -> None:
        graph = FakeGraphRepository()
        result = RecommendFolderUseCase(
            find_folders=FindFoldersUseCase(
                retrieval=FolderRetrievalService(
                    embeddings=FakeEmbeddingProvider(),
                    chunk_vectors=FakeDocumentVectorRepository(),
                    document_vectors=FakeDocumentVectorRepository(),
                    folder_vectors=FakeFolderVectorRepository(),
                    graph=graph,
                    top_k=1,
                ),
                scope_resolver=RelationshipScopeResolver(graph=graph),
            )
        ).execute(
            SourceDocument(
                tenant="tenant-1",
                document_type="document",
                document_id="doc-new",
                source_version="v1",
                title="Startup memo",
                body="창업 아이디어 정리",
            )
        )

        self.assertEqual(result.primary.folder_id, "folder-a")
        self.assertEqual(round(result.confidence, 2), 0.8)


def _chunk(*, document_id: str) -> DocumentChunk:
    return DocumentChunk(
        tenant="tenant-1",
        document_type="document",
        document_id=document_id,
        source_version="v1",
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
        snippet="startup notes",
    )


if __name__ == "__main__":
    unittest.main()
