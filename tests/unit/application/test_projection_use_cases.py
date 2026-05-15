from __future__ import annotations

import unittest

from foldmind_ai_core.application.services.vector_projection_spec import VectorProjectionSpec
from foldmind_ai_core.application.use_cases.projection import (
    HandleDocumentChunkVectorDeletedProjectionUseCase,
    HandleDocumentChunkVectorIndexedProjectionUseCase,
    HandleDocumentGraphDeletedProjectionUseCase,
    HandleDocumentGraphIndexedProjectionUseCase,
    HandleDocumentVectorDeletedProjectionUseCase,
    HandleDocumentVectorIndexedProjectionUseCase,
    HandleFolderGraphDeletedProjectionUseCase,
    HandleFolderGraphIndexedProjectionUseCase,
    HandleFolderVectorDeletedProjectionUseCase,
    HandleFolderVectorIndexedProjectionUseCase,
)
from foldmind_ai_core.domain.indexing.chunks import DocumentChunk
from foldmind_ai_core.domain.indexing.projection_events import (
    DocumentDeletedProjectionEvent,
    DocumentIndexedProjectionEvent,
    FolderDeletedProjectionEvent,
    FolderIndexedProjectionEvent,
)
from foldmind_ai_core.domain.knowledge_graph.models import (
    DocumentConceptProjection,
    DocumentRelationshipProjection,
    FolderRelationshipProjection,
    TagProjection,
)
from foldmind_ai_core.domain.profiling.concepts import profile_concepts_from_labels
from foldmind_ai_core.domain.profiling.models import DocumentProfile
from foldmind_ai_core.domain.reference.documents import (
    DocumentVectorProjection,
    SourceDocument,
)
from foldmind_ai_core.domain.reference.folders import FolderVectorProjection, SourceFolder
from foldmind_ai_core.domain.retrieval.queries import SearchScope
from foldmind_ai_core.domain.retrieval.results import (
    DocumentRetrievalResult,
    FolderRetrievalResult,
    RetrievalResult,
    RetrievedFolder,
)
from foldmind_ai_core.shared.types import Vector

TEST_EMBEDDING_MODEL = "embedding-test-model"
TEST_EMBEDDING_VERSION = "embedding-test-v1"
TEST_INDEX_SCHEMA_VERSION = "index-schema-test-v1"


class FakeEmbeddingProvider:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def embed_texts(self, texts: list[str]) -> list[Vector]:
        self.texts.extend(texts)
        return [[float(len(text))] for text in texts]


class FakeDocumentChunkVectorRepository:
    def __init__(self) -> None:
        self.chunks_by_document: dict[str, tuple[str, ...]] = {}
        self.deleted: list[str] = []

    def replace_document_chunks(
        self,
        *,
        document_id: str,
        chunks: tuple[DocumentChunk, ...],
        vectors: tuple[Vector, ...],
    ) -> None:
        self.chunks_by_document[document_id] = tuple(chunk.chunk_id for chunk in chunks)

    def delete_document_chunks(self, *, document_id: str) -> None:
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


class FakeDocumentVectorRepository:
    def __init__(self) -> None:
        self.documents: dict[str, tuple[str, ...]] = {}
        self.deleted: list[str] = []

    def upsert_document_vector(
        self,
        *,
        projection: DocumentVectorProjection,
        vector: Vector,
    ) -> None:
        self.documents[projection.document_id] = projection.concept_ids

    def delete_document_vector(self, *, document_id: str) -> None:
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


class FakeFolderVectorRepository:
    def __init__(self) -> None:
        self.folders: dict[str, str] = {}
        self.deleted: list[str] = []

    def upsert_folder_vector(
        self,
        *,
        projection: FolderVectorProjection,
        vector: Vector,
    ) -> None:
        self.folders[projection.folder_id] = projection.source_version

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


class FakeGraphRepository:
    def __init__(self) -> None:
        self.relationships: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {}
        self.concepts: dict[str, tuple[str, ...]] = {}
        self.folders: dict[str, str | None] = {}
        self.deleted_documents: list[str] = []
        self.deleted_folders: list[str] = []

    def replace_document_relationships(
        self,
        projection: DocumentRelationshipProjection,
    ) -> None:
        self.relationships[projection.document_id] = (
            projection.folder_ids,
            projection.tag_ids,
        )

    def replace_document_concepts(self, projection: DocumentConceptProjection) -> None:
        self.concepts[projection.document_id] = tuple(
            concept.concept_id for concept in projection.concepts
        )

    def replace_document_projection(
        self,
        *,
        relationships: DocumentRelationshipProjection,
        concepts: DocumentConceptProjection,
    ) -> None:
        self.replace_document_relationships(relationships)
        self.replace_document_concepts(concepts)

    def replace_folder_hierarchy(self, projection: FolderRelationshipProjection) -> None:
        self.folders[projection.folder_id] = projection.parent_folder_id

    def upsert_tag(self, projection: TagProjection) -> None:
        pass

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

    def delete_document(self, *, document_id: str) -> None:
        self.deleted_documents.append(document_id)
        self.relationships.pop(document_id, None)
        self.concepts.pop(document_id, None)

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


class ProjectionUseCaseTests(unittest.TestCase):
    def test_document_indexed_event_projects_each_target_independently(self) -> None:
        embeddings = FakeEmbeddingProvider()
        chunk_vectors = FakeDocumentChunkVectorRepository()
        document_vectors = FakeDocumentVectorRepository()
        graph = FakeGraphRepository()
        event = _document_indexed_projection_event()

        chunk_handler = HandleDocumentChunkVectorIndexedProjectionUseCase(
            embeddings=embeddings,
            chunk_vectors=chunk_vectors,
        )
        document_handler = HandleDocumentVectorIndexedProjectionUseCase(
            embeddings=embeddings,
            document_vectors=document_vectors,
            projection_spec=VectorProjectionSpec(
                embedding_model=TEST_EMBEDDING_MODEL,
                embedding_version=TEST_EMBEDDING_VERSION,
                index_schema_version=TEST_INDEX_SCHEMA_VERSION,
            ),
        )
        graph_handler = HandleDocumentGraphIndexedProjectionUseCase(graph=graph)

        for _ in range(5):
            chunk_handler.handle(event)
            document_handler.handle(event)
            graph_handler.handle(event)

        self.assertEqual(chunk_vectors.chunks_by_document, {"doc-1": ("chunk-1",)})
        self.assertEqual(document_vectors.documents["doc-1"], ("concept-1",))
        self.assertEqual(graph.relationships["doc-1"], (("folder-1",), ("tag-1",)))
        self.assertEqual(graph.concepts["doc-1"], ("concept-1",))
        self.assertEqual(embeddings.texts.count("chunk text"), 5)

    def test_delete_events_project_each_target_independently(self) -> None:
        chunk_vectors = FakeDocumentChunkVectorRepository()
        document_vectors = FakeDocumentVectorRepository()
        folder_vectors = FakeFolderVectorRepository()
        graph = FakeGraphRepository()
        document_event = DocumentDeletedProjectionEvent(
            document_id="doc-1",
        )
        folder_event = FolderDeletedProjectionEvent(
            folder_id="folder-1",
        )

        for _ in range(2):
            HandleDocumentChunkVectorDeletedProjectionUseCase(
                chunk_vectors=chunk_vectors,
            ).handle(document_event)
            HandleDocumentVectorDeletedProjectionUseCase(
                document_vectors=document_vectors,
            ).handle(document_event)
            HandleDocumentGraphDeletedProjectionUseCase(
                graph=graph,
            ).handle(document_event)
            HandleFolderVectorDeletedProjectionUseCase(
                folder_vectors=folder_vectors,
            ).handle(folder_event)
            HandleFolderGraphDeletedProjectionUseCase(
                graph=graph,
            ).handle(folder_event)

        self.assertEqual(chunk_vectors.deleted, ["doc-1", "doc-1"])
        self.assertEqual(document_vectors.deleted, ["doc-1", "doc-1"])
        self.assertEqual(graph.deleted_documents, ["doc-1", "doc-1"])
        self.assertEqual(folder_vectors.deleted, ["folder-1", "folder-1"])
        self.assertEqual(graph.deleted_folders, ["folder-1", "folder-1"])

    def test_folder_indexed_event_projects_each_target_independently(self) -> None:
        embeddings = FakeEmbeddingProvider()
        folder_vectors = FakeFolderVectorRepository()
        graph = FakeGraphRepository()
        event = FolderIndexedProjectionEvent(
            folder=SourceFolder(
                tenant="tenant-1",
                folder_id="folder-1",
                source_version="folder-v1",
                name="Startup",
                parent_folder_id="root",
            )
        )

        HandleFolderVectorIndexedProjectionUseCase(
            embeddings=embeddings,
            folder_vectors=folder_vectors,
            projection_spec=VectorProjectionSpec(
                embedding_model=TEST_EMBEDDING_MODEL,
                embedding_version=TEST_EMBEDDING_VERSION,
                index_schema_version=TEST_INDEX_SCHEMA_VERSION,
            ),
        ).handle(event)
        HandleFolderGraphIndexedProjectionUseCase(graph=graph).handle(event)

        self.assertEqual(folder_vectors.folders, {"folder-1": "folder-v1"})
        self.assertEqual(graph.folders, {"folder-1": "root"})
        self.assertEqual(embeddings.texts, ["Startup"])


def _document_indexed_projection_event() -> DocumentIndexedProjectionEvent:
    document = SourceDocument(
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        source_version="v1",
        title="Title",
        body="Body",
        folder_ids=("folder-1",),
        tag_ids=("tag-1",),
    )
    chunk = DocumentChunk(
        tenant=document.tenant,
        document_type=document.document_type,
        document_id=document.document_id,
        source_version=document.source_version,
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
    profile = DocumentProfile(
        tenant=document.tenant,
        document_type=document.document_type,
        document_id=document.document_id,
        source_version=document.source_version,
        title=document.title,
        summary="Summary",
        profile_version="profile-v1",
        profile_schema_version="1",
        concepts=profile_concepts_from_labels(
            tenant=document.tenant,
            labels=("Concept",),
        ),
    )
    concept = profile.concepts[0]
    profile = DocumentProfile(
        tenant=profile.tenant,
        document_type=profile.document_type,
        document_id=profile.document_id,
        source_version=profile.source_version,
        title=profile.title,
        summary=profile.summary,
        profile_version=profile.profile_version,
        profile_schema_version=profile.profile_schema_version,
        concepts=(
            type(concept)(
                concept_id="concept-1",
                concept_key=concept.concept_key,
                label=concept.label,
                confidence=concept.confidence,
                evidence_chunk_ids=concept.evidence_chunk_ids,
                metadata=concept.metadata,
            ),
        ),
    )
    return DocumentIndexedProjectionEvent(
        document=document,
        chunks=(chunk,),
        profile=profile,
    )


if __name__ == "__main__":
    unittest.main()
