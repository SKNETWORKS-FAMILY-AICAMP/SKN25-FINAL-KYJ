from __future__ import annotations

import sys
import types
import unittest
from collections.abc import Callable


class FakeQdrantModels:
    class Distance:
        COSINE = "Cosine"

    class VectorParams:
        def __init__(self, *, size: int, distance: str) -> None:
            self.size = size
            self.distance = distance

    class PointStruct:
        def __init__(self, *, id: str, vector: list[float], payload: dict[str, object]) -> None:
            self.id = id
            self.vector = vector
            self.payload = payload

    class FilterSelector:
        def __init__(self, *, filter: object) -> None:
            self.filter = filter

    class Filter:
        def __init__(self, *, must: list[object]) -> None:
            self.must = must

    class FieldCondition:
        def __init__(self, *, key: str, match: object) -> None:
            self.key = key
            self.match = match

    class MatchValue:
        def __init__(self, *, value: object) -> None:
            self.value = value

    class MatchAny:
        def __init__(self, *, any: list[object]) -> None:
            self.any = any

    class PayloadSchemaType:
        KEYWORD = "keyword"


def install_provider_sdk_fakes() -> None:
    neo4j_module = types.ModuleType("neo4j")
    neo4j_module.GraphDatabase = object
    sys.modules.setdefault("neo4j", neo4j_module)

    qdrant_module = types.ModuleType("qdrant_client")
    qdrant_module.QdrantClient = object
    qdrant_module.models = FakeQdrantModels
    sys.modules.setdefault("qdrant_client", qdrant_module)


install_provider_sdk_fakes()

import foldmind_ai_core.adapters.outbound.qdrant.client as qdrant_client_module  # noqa: E402
from foldmind_ai_core.adapters.outbound.neo4j.graph_repository import (  # noqa: E402
    Neo4jGraphRepository,
)
from foldmind_ai_core.adapters.outbound.neo4j.search import (  # noqa: E402
    _SIGNAL_WEIGHTS,
    _graph_search_queries,
    folders_for_documents,
    graph_search,
)
from foldmind_ai_core.adapters.outbound.qdrant.client import (  # noqa: E402
    QdrantCollectionClient,
    QdrantCollectionConfig,
)
from foldmind_ai_core.adapters.outbound.qdrant.document_chunk_vector_repository import (  # noqa: E402
    QdrantDocumentChunkVectorRepository,
)
from foldmind_ai_core.adapters.outbound.qdrant.document_vector_repository import (  # noqa: E402
    QdrantDocumentVectorRepository,
)
from foldmind_ai_core.adapters.outbound.qdrant.folder_vector_repository import (  # noqa: E402
    QdrantFolderVectorRepository,
)
from foldmind_ai_core.adapters.outbound.qdrant.settings import QdrantSettings  # noqa: E402
from foldmind_ai_core.domain.indexing.chunks import DocumentChunk  # noqa: E402
from foldmind_ai_core.domain.knowledge_graph.models import (  # noqa: E402
    DocumentConceptProjection,
    DocumentRelationshipProjection,
    FolderRelationshipProjection,
)
from foldmind_ai_core.domain.reference.documents import (  # noqa: E402
    DocumentVectorProjection,
)
from foldmind_ai_core.domain.reference.folders import FolderVectorProjection  # noqa: E402
from foldmind_ai_core.domain.retrieval.queries import SearchScope  # noqa: E402


class FakeQdrantClient:
    def __init__(self) -> None:
        self.upserts: list[tuple[str, list[object]]] = []
        self.deletes: list[tuple[str, object]] = []
        self.queries: list[dict[str, object]] = []
        self.points: list[object] = []

    def upsert(self, *, collection_name: str, points: list[object]) -> None:
        self.upserts.append((collection_name, points))

    def delete(self, *, collection_name: str, points_selector: object) -> None:
        self.deletes.append((collection_name, points_selector))

    def query_points(
        self,
        *,
        collection_name: str,
        query: list[float],
        query_filter: object,
        limit: int,
        with_payload: bool,
    ) -> object:
        self.queries.append(
            {
                "collection_name": collection_name,
                "query": query,
                "query_filter": query_filter,
                "limit": limit,
                "with_payload": with_payload,
            }
        )
        return types.SimpleNamespace(points=self.points)


class FakeNeo4jTransaction:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def run(self, statement: str, **parameters: object) -> None:
        self.statements.append(statement)


class FakeNeo4jSession:
    def __init__(self) -> None:
        self.transactions: list[FakeNeo4jTransaction] = []

    def __enter__(self) -> FakeNeo4jSession:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def execute_write(self, work: Callable[[FakeNeo4jTransaction], None]) -> None:
        transaction = FakeNeo4jTransaction()
        self.transactions.append(transaction)
        work(transaction)


class FakeNeo4jClient:
    def __init__(self) -> None:
        self.sessions: list[FakeNeo4jSession] = []

    def session(self) -> FakeNeo4jSession:
        session = FakeNeo4jSession()
        self.sessions.append(session)
        return session


class FakeNeo4jReadSession:
    def __init__(self, records: list[dict[str, object]]) -> None:
        self.records = records

    def run(self, statement: str, **parameters: object) -> list[dict[str, object]]:
        return self.records


class VectorAndGraphAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_models = qdrant_client_module.models
        qdrant_client_module.models = FakeQdrantModels

    def tearDown(self) -> None:
        qdrant_client_module.models = self.previous_models

    def test_qdrant_stores_write_chunk_document_and_folder_payloads(self) -> None:
        client = FakeQdrantClient()
        chunk_vectors = QdrantDocumentChunkVectorRepository(
            client=_qdrant_collection_client("document_chunks", client),
        )
        document_vectors = QdrantDocumentVectorRepository(
            client=_qdrant_collection_client("documents", client),
        )
        folder_vectors = QdrantFolderVectorRepository(
            client=_qdrant_collection_client("folders", client),
        )

        chunk_vectors.replace_document_chunks(
            document_id="doc-1",
            chunks=(
                DocumentChunk(
                    tenant="tenant-1",
                    document_type="document",
                    document_id="doc-1",
                    source_version="v1",
                    chunk_id="doc-1:chunk:0",
                    chunk_index=0,
                    chunking_version="chunking-test-v1",
                    text="startup evidence",
                    text_hash="hash-1",
                    start_offset=0,
                    end_offset=16,
                    embedding_model="test-embedding",
                    embedding_version="test-v1",
                    index_schema_version="schema-v1",
                ),
            ),
            vectors=([0.1],),
        )
        document_vectors.upsert_document_vector(
            projection=DocumentVectorProjection(
                tenant="tenant-1",
                document_type="document",
                document_id="doc-1",
                source_version="v1",
                profile_version="profile-v1",
                profile_schema_version="1",
                concept_ids=("concept-1",),
                profile_confidence=0.8,
                embedding_input="startup summary",
                embedding_input_hash="hash-1",
                embedding_model="test-embedding",
                embedding_version="test-v1",
                index_schema_version="schema-v1",
            ),
            vector=[0.2],
        )
        folder_vectors.upsert_folder_vector(
            projection=FolderVectorProjection(
                tenant="tenant-1",
                folder_id="folder-1",
                source_version="folder-v1",
                embedding_input="Founding\n\n/Company/Founding\n\nstartup folder",
                embedding_input_hash="folder-hash-1",
                embedding_model="test-embedding",
                embedding_version="test-v1",
                index_schema_version="schema-v1",
            ),
            vector=[0.3],
        )

        collections = [collection for collection, _ in client.upserts]
        point_ids = [points[0].id for _, points in client.upserts]
        payloads = [points[0].payload for _, points in client.upserts]
        self.assertEqual(collections, ["document_chunks", "documents", "folders"])
        self.assertEqual(point_ids, ["doc-1:chunk:0", "doc-1", "folder-1"])
        self.assertEqual(payloads[0]["kind"], "document_chunk")
        self.assertEqual(payloads[0]["source_version"], "v1")
        self.assertEqual(payloads[0]["text_hash"], "hash-1")
        self.assertEqual(payloads[0]["embedding_model"], "test-embedding")
        self.assertEqual(payloads[0]["embedding_version"], "test-v1")
        self.assertEqual(payloads[0]["index_schema_version"], "schema-v1")
        self.assertNotIn("embedding_input_hash", payloads[0])
        self.assertNotIn("folder_ids", payloads[0])
        self.assertNotIn("tag_ids", payloads[0])
        self.assertEqual(payloads[1]["kind"], "document")
        self.assertEqual(payloads[1]["concept_ids"], ["concept-1"])
        self.assertEqual(payloads[1]["profile_confidence"], 0.8)
        self.assertEqual(payloads[1]["embedding_input_hash"], "hash-1")
        self.assertNotIn("title_snapshot", payloads[1])
        self.assertNotIn("summary", payloads[1])
        self.assertNotIn("topics", payloads[1])
        self.assertNotIn("folder_ids", payloads[1])
        self.assertNotIn("tag_ids", payloads[1])
        self.assertEqual(payloads[2]["kind"], "folder")
        self.assertEqual(payloads[2]["source_version"], "folder-v1")
        self.assertEqual(payloads[2]["embedding_input_hash"], "folder-hash-1")
        self.assertNotIn("name_snapshot", payloads[2])
        self.assertNotIn("path_snapshot", payloads[2])
        self.assertNotIn("description", payloads[2])
        self.assertNotIn("parent_folder_id", payloads[2])
        self.assertNotIn("metadata", payloads[2])

    def test_qdrant_folder_search_filters_scope_folder_ids(self) -> None:
        client = FakeQdrantClient()
        folder_vectors = QdrantFolderVectorRepository(
            client=_qdrant_collection_client("folders", client),
        )

        folder_vectors.search_folders(
            tenant="tenant-1",
            query_vector=[0.3],
            top_k=5,
            scope=SearchScope(
                document_type="document",
                document_id="doc-1",
                folder_ids=("folder-a", "folder-b"),
                tag_ids=("startup",),
            ),
        )

        qdrant_filter = client.queries[0]["query_filter"]
        conditions = {condition.key: condition.match for condition in qdrant_filter.must}
        self.assertEqual(conditions["tenant"].value, "tenant-1")
        self.assertEqual(conditions["folder_id"].any, ["folder-a", "folder-b"])
        self.assertNotIn("document_type", conditions)
        self.assertNotIn("document_id", conditions)
        self.assertNotIn("tag_ids", conditions)

    def test_qdrant_search_does_not_return_blank_ids(self) -> None:
        chunk_client = FakeQdrantClient()
        chunk_client.points = [
            types.SimpleNamespace(
                score=1.0,
                payload={
                    "tenant": "tenant-1",
                    "document_type": "document",
                    "document_id": " ",
                    "source_version": "v1",
                    "chunk_id": "chunk-blank",
                    "chunk_index": 0,
                    "text": "blank",
                    "text_hash": "hash-blank",
                    "start_offset": 0,
                    "end_offset": 5,
                },
            ),
        ]
        document_client = FakeQdrantClient()
        document_client.points = [
            types.SimpleNamespace(
                score=1.0,
                payload={
                    "tenant": "tenant-1",
                    "document_type": "document",
                    "document_id": " ",
                    "source_version": "v1",
                    "profile_schema_version": "1",
                    "concept_ids": [],
                },
            ),
            types.SimpleNamespace(
                score=0.8,
                payload={
                    "tenant": "tenant-1",
                    "document_type": "document",
                    "document_id": "doc-1",
                    "source_version": "v1",
                    "profile_schema_version": "1",
                    "concept_ids": [],
                },
            ),
        ]
        folder_client = FakeQdrantClient()
        folder_client.points = [
            types.SimpleNamespace(
                score=0.7,
                payload={
                    "tenant": "tenant-1",
                    "folder_id": " ",
                    "source_version": "folder-v1",
                },
            ),
        ]
        chunk_vectors = QdrantDocumentChunkVectorRepository(
            client=_qdrant_collection_client("chunks", chunk_client),
        )
        document_vectors = QdrantDocumentVectorRepository(
            client=_qdrant_collection_client("documents", document_client),
        )
        folder_vectors = QdrantFolderVectorRepository(
            client=_qdrant_collection_client("folders", folder_client),
        )

        self.assertEqual(
            chunk_vectors.search_chunks(
                tenant="tenant-1",
                query_vector=[0.1],
                top_k=5,
            ),
            [],
        )
        documents = document_vectors.search_documents(
            tenant="tenant-1",
            query_vector=[0.1],
            top_k=5,
        )
        self.assertEqual(
            [result.document.document_id for result in documents],
            ["doc-1"],
        )
        self.assertEqual(
            folder_vectors.search_folders(
                tenant="tenant-1",
                query_vector=[0.1],
                top_k=5,
            ),
            [],
        )

    def test_neo4j_search_does_not_return_blank_ids(self) -> None:
        session = FakeNeo4jReadSession(
            [
                {
                    "d": {
                        "tenant": "tenant-1",
                        "document_id": " ",
                        "source_version": "v1",
                    },
                    "confidence": 1.0,
                },
                {
                    "d": {
                        "tenant": "tenant-1",
                        "document_id": "doc-1",
                        "source_version": "v1",
                    },
                    "confidence": 1.0,
                },
            ]
        )

        results = graph_search(
            session,
            tenant="tenant-1",
            query_text="startup",
            top_k=5,
            scope=None,
        )
        folders_by_document = folders_for_documents(
            FakeNeo4jReadSession(
                [
                    {"document_id": " ", "folders": [{"folder_id": "folder-blank"}]},
                    {
                        "document_id": "doc-1",
                        "folders": [
                            {
                                "tenant": "tenant-1",
                                "folder_id": "folder-1",
                                "source_version": "folder-v1",
                            },
                            {
                                "tenant": "tenant-1",
                                "folder_id": " ",
                                "source_version": "folder-v1",
                            },
                        ],
                    },
                ]
            ),
            tenant="tenant-1",
            document_ids=("doc-1",),
        )

        self.assertEqual(
            [result.document.document_id for result in results],
            ["doc-1"],
        )
        self.assertEqual(tuple(folders_by_document), ("doc-1",))
        self.assertEqual(folders_by_document["doc-1"][0].folder_id, "folder-1")

    def test_neo4j_search_uses_only_projected_signals(self) -> None:
        queries = "\n".join(query for query, _ in _graph_search_queries())
        signal_types = [signal_type for _, signal_type in _graph_search_queries()]

        self.assertEqual(_SIGNAL_WEIGHTS["ABOUT"], 0.75)
        self.assertEqual(_SIGNAL_WEIGHTS["HAS_TAG"], 0.90)
        self.assertEqual(_SIGNAL_WEIGHTS["TAG_REPRESENTS"], 0.60)
        self.assertEqual(_SIGNAL_WEIGHTS["IN_FOLDER"], 0.75)
        self.assertIn("FOLDER_DESCENDANT", signal_types)
        self.assertIn("FOLDER_SIBLING", signal_types)
        self.assertNotIn("related.confidence >= $related_to_min_confidence", queries)
        self.assertNotIn("coalesce(related.validated, false) = true", queries)
        self.assertNotIn("RELATED_TO", queries)
        self.assertNotIn("FOLDER_ABOUT", queries)
        self.assertNotIn("MENTIONS", signal_types)
        self.assertNotIn("SUGGESTED_TAG", signal_types)
        self.assertNotIn("SUGGESTED_FOLDER", signal_types)
        self.assertNotIn("FOLDER_ABOUT", signal_types)
        self.assertNotIn("RELATED_TO", signal_types)

    def test_neo4j_replaces_document_graph_projection_in_one_write_transaction(
        self,
    ) -> None:
        client = FakeNeo4jClient()
        repository = Neo4jGraphRepository(client=client)  # type: ignore[arg-type]

        repository.replace_document_projection(
            relationships=DocumentRelationshipProjection(
                tenant="tenant-1",
                document_type="document",
                document_id="doc-1",
                source_version="v1",
                folder_ids=("folder-1",),
                tag_ids=("tag-1",),
            ),
            concepts=DocumentConceptProjection(
                tenant="tenant-1",
                document_type="document",
                document_id="doc-1",
                source_version="v1",
                title="Title",
                profile_version="profile-v1",
            ),
        )

        self.assertEqual(len(client.sessions), 1)
        self.assertEqual(len(client.sessions[0].transactions), 1)
        statements = "\n".join(client.sessions[0].transactions[0].statements)
        self.assertIn("IN_FOLDER|HAS_TAG", statements)
        self.assertIn("ABOUT", statements)

    def test_neo4j_tombstones_folder_and_removes_folder_edges(self) -> None:
        client = FakeNeo4jClient()
        repository = Neo4jGraphRepository(client=client)  # type: ignore[arg-type]

        repository.delete_folder(folder_id="folder-1")

        statements = "\n".join(client.sessions[0].transactions[0].statements)
        self.assertIn("MERGE (f:Folder {folder_id: $folder_id})", statements)
        self.assertIn("f.deleted = true", statements)
        self.assertIn("outgoing_child_of:CHILD_OF", statements)
        self.assertIn("incoming_child_of:CHILD_OF", statements)
        self.assertIn("in_folder:IN_FOLDER", statements)
        self.assertNotIn("DETACH DELETE", statements)

    def test_neo4j_document_relationships_do_not_overwrite_folder_properties(
        self,
    ) -> None:
        client = FakeNeo4jClient()
        repository = Neo4jGraphRepository(client=client)  # type: ignore[arg-type]

        repository.replace_document_relationships(
            DocumentRelationshipProjection(
                tenant="tenant-1",
                document_type="document",
                document_id="doc-1",
                source_version="v1",
                folder_ids=("folder-1",),
            )
        )

        statements = "\n".join(client.sessions[0].transactions[0].statements)
        self.assertIn("ON CREATE SET f.tenant = $tenant", statements)
        self.assertIn("f.deleted = coalesce(f.deleted, false)", statements)
        self.assertIn("WHERE coalesce(f.deleted, false) = false", statements)
        self.assertNotIn("f.label = $label", statements)
        self.assertNotIn("f.path_snapshot = $path_snapshot", statements)
        self.assertNotIn("f.parent_folder_id = $parent_folder_id", statements)
        self.assertNotIn("f.metadata_json = $metadata_json", statements)

    def test_neo4j_folder_index_clears_tombstone_and_rebuilds_hierarchy(
        self,
    ) -> None:
        client = FakeNeo4jClient()
        repository = Neo4jGraphRepository(client=client)  # type: ignore[arg-type]

        repository.replace_folder_hierarchy(
            FolderRelationshipProjection(
                tenant="tenant-1",
                folder_id="folder-1",
                source_version="folder-v1",
                parent_folder_id="root",
            )
        )

        statements = "\n".join(client.sessions[0].transactions[0].statements)
        self.assertIn("f.deleted = false", statements)
        self.assertIn("MERGE (child)-[r:CHILD_OF]->(parent)", statements)
        self.assertIn("WHERE coalesce(parent.deleted, false) = false", statements)

def _qdrant_collection_client(
    collection_name: str,
    client: FakeQdrantClient,
) -> QdrantCollectionClient:
    return QdrantCollectionClient(
        config=QdrantCollectionConfig(collection_name, 1),
        settings=QdrantSettings(url="http://qdrant.test"),
        client=client,
    )


if __name__ == "__main__":
    unittest.main()
