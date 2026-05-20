from __future__ import annotations

import sys
import types
import unittest
from dataclasses import dataclass


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
        def __init__(
            self,
            *,
            key: str,
            match: object | None = None,
            range: object | None = None,
            datetime_range: object | None = None,
        ) -> None:
            self.key = key
            self.match = match
            self.range = range
            self.datetime_range = datetime_range

    class MatchValue:
        def __init__(self, *, value: object) -> None:
            self.value = value

    class MatchAny:
        def __init__(self, *, any: list[object]) -> None:
            self.any = any

    class Range:
        def __init__(self, **values: object) -> None:
            self.values = values

    class DatetimeRange:
        def __init__(self, **values: object) -> None:
            self.values = values

    class PayloadSchemaType:
        KEYWORD = "keyword"
        DATETIME = "datetime"
        INTEGER = "integer"


def install_provider_sdk_fakes() -> None:
    neo4j_module = types.ModuleType("neo4j")
    neo4j_module.GraphDatabase = object
    sys.modules.setdefault("neo4j", neo4j_module)

    qdrant_module = types.ModuleType("qdrant_client")
    qdrant_module.QdrantClient = object
    qdrant_module.models = FakeQdrantModels
    sys.modules.setdefault("qdrant_client", qdrant_module)


install_provider_sdk_fakes()

from foldmind_ai_core.adapters.outbound.neo4j.schema import ensure_neo4j_schema  # noqa: E402
from foldmind_ai_core.adapters.outbound.neo4j.stores.graph_store import (  # noqa: E402
    Neo4jGraphStore,
)
from foldmind_ai_core.adapters.outbound.qdrant.client import (  # noqa: E402
    QdrantCollectionClient,
    QdrantCollectionConfig,
)
from foldmind_ai_core.adapters.outbound.qdrant.settings import QdrantSettings  # noqa: E402
from foldmind_ai_core.adapters.outbound.qdrant.stores.document_chunk_vector_store import (  # noqa: E402
    QdrantDocumentChunkVectorStore,
)
from foldmind_ai_core.adapters.outbound.qdrant.stores.document_vector_store import (  # noqa: E402
    QdrantDocumentVectorStore,
)
from foldmind_ai_core.adapters.outbound.qdrant.stores.folder_vector_store import (  # noqa: E402
    QdrantFolderVectorStore,
)
from foldmind_ai_core.adapters.outbound.qdrant.stores.signal_vector_store import (  # noqa: E402
    QdrantSignalVectorStore,
)
from foldmind_ai_core.core.application.models.projection_inputs import (  # noqa: E402
    ProjectionSignalEvidence,
)
from foldmind_ai_core.core.application.projections.graph import (  # noqa: E402
    DocumentFolderRelationProjection,
    DocumentRelationshipProjection,
    DocumentSignalProjection,
    DocumentSignalNodeProjection,
    FolderRelationshipProjection,
    FolderSignalProjection,
    FolderSignalNodeProjection,
)
from foldmind_ai_core.core.application.projections.vector import (  # noqa: E402
    DocumentChunkVectorProjection,
    DocumentSignalVectorProjection,
    DocumentVectorProjection,
    FolderSignalVectorProjection,
    FolderVectorProjection,
)
from foldmind_ai_core.core.application.queries.retrieval import SearchScope  # noqa: E402
from foldmind_ai_core.shared.internal_ids import stable_internal_id  # noqa: E402
from foldmind_ai_core.shared.validation import InvalidInputError  # noqa: E402


class FakeQdrantClient:
    def __init__(self) -> None:
        self.created_collections: list[tuple[str, object]] = []
        self.payload_indexes: list[tuple[str, str, object]] = []
        self.upserts: list[tuple[str, list[object]]] = []
        self.deletes: list[tuple[str, object]] = []
        self.queries: list[dict[str, object]] = []
        self.points: list[object] = []

    def collection_exists(self, collection_name: str) -> bool:
        return any(name == collection_name for name, _ in self.created_collections)

    def create_collection(self, *, collection_name: str, vectors_config: object) -> None:
        self.created_collections.append((collection_name, vectors_config))

    def create_payload_index(
        self,
        *,
        collection_name: str,
        field_name: str,
        field_schema: object,
    ) -> None:
        self.payload_indexes.append((collection_name, field_name, field_schema))

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


@dataclass
class FakeScoredPoint:
    payload: dict[str, object]
    score: float = 0.9


class FakeNeo4jClient:
    def __init__(self) -> None:
        self.sessions: list[FakeNeo4jSession] = []

    def session(self) -> "FakeNeo4jSession":
        session = FakeNeo4jSession()
        self.sessions.append(session)
        return session


class FakeNeo4jSession:
    def __init__(self) -> None:
        self.transactions: list[FakeNeo4jTransaction] = []
        self.statements: list[str] = []

    def __enter__(self) -> "FakeNeo4jSession":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute_write(self, callback: object) -> None:
        tx = FakeNeo4jTransaction()
        self.transactions.append(tx)
        callback(tx)

    def write_transaction(self, callback: object) -> None:
        self.execute_write(callback)

    def run(self, statement: str, **parameters: object) -> list[object]:
        self.statements.append(statement)
        return []


class FakeNeo4jTransaction:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    @property
    def statements(self) -> list[str]:
        return [statement for statement, _ in self.calls]

    def run(self, statement: str, **parameters: object) -> list[object]:
        self.calls.append((statement, parameters))
        return []


class VectorAdapterTests(unittest.TestCase):
    def test_qdrant_collection_setup_creates_payload_indexes(self) -> None:
        client = FakeQdrantClient()
        collection = QdrantCollectionClient(
            config=QdrantCollectionConfig(
                collection_name="documents",
                vector_size=3,
                payload_indexes=("tenant", "updated_at", "index_input_digest"),
            ),
            settings=QdrantSettings(url="http://qdrant:6333"),
            client=client,
        )

        collection.setup_collection()

        self.assertEqual(len(client.created_collections), 1)
        self.assertEqual(
            client.payload_indexes,
            [
                ("documents", "tenant", "keyword"),
                ("documents", "updated_at", "datetime"),
                ("documents", "index_input_digest", "keyword"),
            ],
        )

    def test_qdrant_stores_write_current_projection_payloads(self) -> None:
        client = FakeQdrantClient()
        chunk_vectors = QdrantDocumentChunkVectorStore(
            client=_qdrant_collection_client("document_chunks", client),
        )
        document_vectors = QdrantDocumentVectorStore(
            client=_qdrant_collection_client("documents", client),
        )
        signal_vectors = QdrantSignalVectorStore(
            client=_qdrant_collection_client("signals", client),
        )
        folder_vectors = QdrantFolderVectorStore(
            client=_qdrant_collection_client("folders", client),
        )

        chunk_vectors.replace_document_chunks(
            tenant="tenant-1",
            document_id="doc-1",
            chunks=(_chunk_projection(),),
            vectors=([0.1],),
        )
        document_vectors.upsert_document_vector(
            projection=_document_projection(),
            vector=[0.2],
        )
        signal_vectors.replace_document_signals(
            tenant="tenant-1",
            document_id="doc-1",
            signals=(_signal_projection(),),
            vectors=([0.3],),
        )
        signal_vectors.replace_folder_signals(
            tenant="tenant-1",
            folder_id="folder-1",
            signals=(_folder_signal_projection(),),
            vectors=([0.35],),
        )
        folder_vectors.upsert_folder_vector(
            projection=_folder_projection(),
            vector=[0.4],
        )

        collections = [collection for collection, _ in client.upserts]
        point_ids = [points[0].id for _, points in client.upserts]
        payloads = [points[0].payload for _, points in client.upserts]
        self.assertEqual(
            collections,
            ["document_chunks", "documents", "signals", "signals", "folders"],
        )
        self.assertEqual(
            point_ids,
            [
                stable_internal_id(
                    "qdrant-point",
                    "document_chunks",
                    "chunk-1",
                ),
                stable_internal_id(
                    "documents",
                    "document",
                    "doc-1",
                    "index-input-v1",
                ),
                stable_internal_id(
                    "signals",
                    "signal-vector",
                    "document",
                    "doc-1",
                    "signal-1",
                    "index-input-v1",
                ),
                stable_internal_id(
                    "signals",
                    "signal-vector",
                    "folder",
                    "folder-1",
                    "folder-signal-1",
                    "folder-signal-input-v1",
                ),
                stable_internal_id(
                    "folders",
                    "folder",
                    "folder-1",
                    "folder-input-v1",
                ),
            ],
        )
        self.assertEqual(payloads[1]["kind"], "document")
        self.assertEqual(payloads[1]["content_digest"], "content-digest-1")
        self.assertEqual(payloads[1]["index_input_digest"], "index-input-v1")
        self.assertNotIn("concept_ids", payloads[1])
        self.assertEqual(payloads[2]["kind"], "signal")
        self.assertEqual(payloads[2]["owner_kind"], "document")
        self.assertEqual(payloads[2]["document_type"], "document")
        self.assertEqual(payloads[2]["content_digest"], "content-digest-1")
        self.assertEqual(payloads[2]["index_input_digest"], "index-input-v1")
        self.assertEqual(payloads[2]["evidence"][0]["chunk_id"], "chunk-1")
        self.assertEqual(payloads[3]["kind"], "signal")
        self.assertEqual(payloads[3]["owner_kind"], "folder")
        self.assertEqual(payloads[3]["folder_id"], "folder-1")
        self.assertEqual(payloads[3]["attributes"]["responsibility_score"], 0.8)
        self.assertEqual(payloads[3]["related_document_id"], "doc-2")
        self.assertNotIn("snapshot_digest", payloads[4])

    def test_qdrant_signal_search_restores_evidence_and_filters_by_document(self) -> None:
        client = FakeQdrantClient()
        store = QdrantSignalVectorStore(
            client=_qdrant_collection_client("signals", client),
        )
        client.points = [
            FakeScoredPoint(
                payload={
                    "kind": "signal",
                    "signal_id": "signal-1",
                    "tenant": "tenant-1",
                    "owner_kind": "document",
                    "document_type": "document",
                    "document_id": "doc-1",
                    "folder_id": None,
                    "signal_type": "issue",
                    "signal_key": "issue-key",
                    "text": "Repeated concern",
                    "source_version": "v1",
                    "evidence": [
                        {
                            "chunk_id": "chunk-1",
                            "quote": "Concern quote",
                            "start_offset": 0,
                            "end_offset": 13,
                            "metadata": {"page": 1},
                        }
                    ],
                    "attributes": {},
                    "related_document_id": None,
                    "confidence": 0.8,
                    "embedding_input_hash": "hash-1",
                    "embedding_model": "embedding",
                    "embedding_version": "v1",
                    "index_schema_version": "schema-v1",
                    "metadata": {},
                }
            )
        ]

        results = store.search_signals(
            tenant="tenant-1",
            query_vector=[0.1],
            top_k=5,
            signal_type="issue",
            scope=SearchScope(document_id="doc-1"),
        )

        self.assertEqual(results[0].signal.signal_id, "signal-1")
        self.assertEqual(results[0].signal.owner_kind, "document")
        self.assertEqual(results[0].signal.evidence[0].quote, "Concern quote")
        must = client.queries[0]["query_filter"].must
        filters = {
            condition.key: condition.match.value
            for condition in must
            if getattr(condition.match, "value", None) is not None
        }
        self.assertEqual(filters["document_id"], "doc-1")
        self.assertEqual(filters["owner_kind"], "document")

    def test_qdrant_signal_search_includes_folder_signals_by_default(self) -> None:
        client = FakeQdrantClient()
        store = QdrantSignalVectorStore(
            client=_qdrant_collection_client("signals", client),
        )
        client.points = [
            FakeScoredPoint(payload=_signal_payload(owner_kind="document")),
            FakeScoredPoint(payload=_signal_payload(owner_kind="folder")),
        ]

        results = store.search_signals(
            tenant="tenant-1",
            query_vector=[0.1],
            top_k=5,
        )

        self.assertEqual(
            [result.signal.owner_kind for result in results],
            ["document", "folder"],
        )
        self.assertEqual(results[1].signal.folder_id, "folder-1")
        self.assertEqual(results[1].signal.related_document_id, "doc-2")
        filters = {
            condition.key: condition.match.value
            for condition in client.queries[0]["query_filter"].must
            if getattr(condition.match, "value", None) is not None
        }
        self.assertNotIn("owner_kind", filters)

    def test_qdrant_folder_signal_scope_filters_by_folder_owner(self) -> None:
        client = FakeQdrantClient()
        store = QdrantSignalVectorStore(
            client=_qdrant_collection_client("signals", client),
        )
        client.points = [FakeScoredPoint(payload=_signal_payload(owner_kind="folder"))]

        results = store.search_signals(
            tenant="tenant-1",
            query_vector=[0.1],
            top_k=5,
            scope=SearchScope(folder_ids=("folder-1",)),
        )

        self.assertEqual(results[0].signal.owner_kind, "folder")
        must = client.queries[0]["query_filter"].must
        filters = {
            condition.key: condition.match.value
            for condition in must
            if getattr(condition.match, "value", None) is not None
        }
        self.assertEqual(filters["owner_kind"], "folder")
        any_filters = {
            condition.key: condition.match.any
            for condition in must
            if getattr(condition.match, "any", None) is not None
        }
        self.assertEqual(any_filters["folder_id"], ["folder-1"])

    def test_qdrant_rejects_invalid_vector_inputs(self) -> None:
        client = FakeQdrantClient()
        document_vectors = QdrantDocumentVectorStore(
            client=_qdrant_collection_client("documents", client),
        )

        with self.assertRaises(InvalidInputError):
            document_vectors.upsert_document_vector(
                projection=_document_projection(),
                vector=[float("nan")],
            )
        with self.assertRaises(InvalidInputError):
            document_vectors.search_documents(
                tenant="tenant-1",
                query_vector=[float("inf")],
                top_k=5,
            )
        self.assertEqual(client.upserts, [])


class GraphAdapterTests(unittest.TestCase):
    def test_neo4j_schema_uses_signal_identity(self) -> None:
        session = FakeNeo4jSession()

        ensure_neo4j_schema(session)

        statements = "\n".join(session.statements)
        self.assertIn(
            "FOR (n:Document) REQUIRE n.document_id IS UNIQUE",
            statements,
        )
        self.assertIn(
            "FOR (n:Folder) REQUIRE n.folder_id IS UNIQUE",
            statements,
        )
        self.assertNotIn(
            "FOR (n:Document) REQUIRE (n.tenant, n.document_id) IS UNIQUE",
            statements,
        )
        self.assertNotIn(
            "FOR (n:Folder) REQUIRE (n.tenant, n.folder_id) IS UNIQUE",
            statements,
        )
        self.assertIn(
            "FOR (n:DocumentSignal) REQUIRE n.signal_id IS UNIQUE",
            statements,
        )
        self.assertIn(
            "FOR (n:FolderSignal) REQUIRE n.signal_id IS UNIQUE",
            statements,
        )
        self.assertNotIn(
            "FOR (n:DocumentSignal) REQUIRE (n.tenant, n.signal_id) IS UNIQUE",
            statements,
        )
        self.assertNotIn(
            "FOR (n:FolderSignal) REQUIRE (n.tenant, n.signal_id) IS UNIQUE",
            statements,
        )
        self.assertNotIn("FOR (n:Concept)", statements)
        self.assertNotIn("concept_tenant_key", statements)
        self.assertNotIn("concept_identity", statements)

    def test_neo4j_replaces_document_projection_with_signals(self) -> None:
        client = FakeNeo4jClient()
        repository = Neo4jGraphStore(client=client)

        repository.replace_document_projection(
            relationships=DocumentRelationshipProjection(
                tenant="tenant-1",
                document_type="document",
                document_id="doc-1",
                source_version="v1",
                content_digest="content-digest-1",
                created_at="2026-05-01T10:00:00+09:00",
                updated_at="2026-05-02T11:00:00+09:00",
            ),
            signals=DocumentSignalProjection(
                tenant="tenant-1",
                document_type="document",
                document_id="doc-1",
                source_version="v1",
                content_digest="content-digest-1",
                index_input_digest="index-input-v1",
                created_at="2026-05-01T10:00:00+09:00",
                updated_at="2026-05-02T11:00:00+09:00",
                title="Title",
                signals=(
                    DocumentSignalNodeProjection(
                        signal_id="signal-1",
                        tenant="tenant-1",
                        signal_type="concept",
                        signal_key="startup",
                        text="Startup",
                        document_id="doc-1",
                        source_version="v1",
                        content_digest="content-digest-1",
                        index_input_digest="index-input-v1",
                        confidence=0.9,
                        generation_model="test-model",
                    ),
                ),
            ),
        )

        tx = client.sessions[0].transactions[0]
        statements = "\n".join(tx.statements)
        self.assertNotIn("IN_FOLDER", statements)
        self.assertNotIn("HAS_TAG", statements)
        self.assertIn("HAS_SIGNAL", statements)
        self.assertIn("MERGE (d:Document {document_id: $document_id})", statements)
        self.assertIn("MATCH (d:Document {document_id: $document_id})", statements)
        self.assertNotIn("MATCH (f:Folder {folder_id: $folder_id})", statements)
        self.assertNotIn("MERGE (d:Document {\n            tenant: $tenant,", statements)
        self.assertNotIn("MATCH (d:Document {\n            tenant: $tenant,", statements)
        self.assertNotIn(
            "MATCH (f:Folder {tenant: $tenant, folder_id: $folder_id})",
            statements,
        )
        self.assertNotIn("document_type: $document_type", statements)
        self.assertIn("d.document_type = $document_type", statements)
        self.assertIn(
            "MERGE (s:DocumentSignal {signal_id: $signal_id})",
            statements,
        )
        self.assertIn("MATCH (s:DocumentSignal {document_id: $document_id})", statements)
        self.assertIn("s.content_digest = $content_digest", statements)
        self.assertIn("r.content_digest = $content_digest", statements)
        self.assertNotIn(
            "MERGE (s:DocumentSignal {tenant: $tenant, signal_id: $signal_id})",
            statements,
        )
        self.assertNotIn(
            "MATCH (s:DocumentSignal {tenant: $tenant, signal_id: $signal_id})",
            statements,
        )
        self.assertNotIn(":Concept", statements)
        self.assertNotIn("ABOUT", statements)

    def test_neo4j_replaces_document_folder_relations_independently(self) -> None:
        client = FakeNeo4jClient()
        repository = Neo4jGraphStore(client=client)

        repository.replace_document_folder_relations(
            projection=DocumentFolderRelationProjection(
                tenant="tenant-1",
                document_id="doc-1",
                source_version="v2",
                folder_ids=("folder-2",),
            )
        )

        tx = client.sessions[0].transactions[0]
        statements = "\n".join(tx.statements)
        self.assertIn("MERGE (d:Document {document_id: $document_id})", statements)
        self.assertIn(
            "MATCH (d:Document {document_id: $document_id})-[r:IN_FOLDER]->()",
            statements,
        )
        self.assertIn("MATCH (f:Folder {folder_id: $folder_id})", statements)
        self.assertIn("r.source_version = $source_version", statements)

    def test_neo4j_tombstones_folder_and_removes_folder_edges(self) -> None:
        client = FakeNeo4jClient()
        repository = Neo4jGraphStore(client=client)

        repository.delete_folder(folder_id="folder-1")

        statements = "\n".join(client.sessions[0].transactions[0].statements)
        self.assertIn(
            "MATCH (f:Folder {folder_id: $folder_id})",
            statements,
        )
        self.assertNotIn("MERGE (f:Folder {folder_id: $folder_id})", statements)
        self.assertIn("f.deleted = true", statements)
        self.assertIn("outgoing_child_of:CHILD_OF", statements)
        self.assertIn("incoming_child_of:CHILD_OF", statements)
        self.assertIn(
            "OPTIONAL MATCH (:Document)-[in_folder:IN_FOLDER]->(f)",
            statements,
        )
        self.assertIn("in_folder:IN_FOLDER", statements)
        self.assertIn("DETACH DELETE s", statements)

    def test_neo4j_deletes_folder_signal_projection(self) -> None:
        client = FakeNeo4jClient()
        repository = Neo4jGraphStore(client=client)

        repository.delete_folder_signals(folder_id="folder-1")

        tx = client.sessions[0].transactions[0]
        statements = "\n".join(tx.statements)
        self.assertIn("MATCH (s:FolderSignal {folder_id: $folder_id})", statements)
        self.assertIn("DETACH DELETE s", statements)
        self.assertEqual(tx.calls[0][1]["folder_id"], "folder-1")

    def test_neo4j_folder_index_clears_tombstone_and_rebuilds_hierarchy(self) -> None:
        client = FakeNeo4jClient()
        repository = Neo4jGraphStore(client=client)

        repository.replace_folder_projection(
            relationships=FolderRelationshipProjection(
                tenant="tenant-1",
                folder_id="folder-1",
                source_version="folder-v1",
                name="Folder",
                created_at="2026-05-01T10:00:00+09:00",
                updated_at="2026-05-02T11:00:00+09:00",
                parent_folder_id="root",
            ),
        )
        repository.replace_folder_signals(
            signals=FolderSignalProjection(
                tenant="tenant-1",
                folder_id="folder-1",
                source_version="folder-v1",
                index_input_digest="folder-signal-input-v2",
                signals=(
                    FolderSignalNodeProjection(
                        signal_id="folder-signal-1",
                        tenant="tenant-1",
                        folder_id="folder-1",
                        source_version="folder-v1",
                        signal_type="outlier_document",
                        signal_key="doc-2",
                        text="Outlier document",
                        related_document_id="doc-2",
                        confidence=0.7,
                        index_input_digest="folder-signal-input-v2",
                    ),
                ),
            ),
        )

        statements = "\n".join(client.sessions[0].transactions[0].statements)
        self.assertIn("MERGE (f:Folder {folder_id: $folder_id})", statements)
        self.assertNotIn(
            "MERGE (f:Folder {tenant: $tenant, folder_id: $folder_id})",
            statements,
        )
        self.assertIn("MATCH (child:Folder {folder_id: $folder_id})", statements)
        self.assertIn(
            "MATCH (parent:Folder {folder_id: $parent_folder_id})",
            statements,
        )
        self.assertNotIn(
            "MATCH (child:Folder {tenant: $tenant, folder_id: $folder_id})",
            statements,
        )
        self.assertIn("f.deleted = false", statements)
        self.assertNotIn("snapshot_digest", statements)
        self.assertIn("CHILD_OF", statements)
        self.assertNotIn("MERGE (s:FolderSignal {signal_id: $signal_id})", statements)

        signal_statements = "\n".join(client.sessions[1].transactions[0].statements)
        self.assertIn("MERGE (s:FolderSignal {signal_id: $signal_id})", signal_statements)
        self.assertIn("s.index_input_digest = $index_input_digest", signal_statements)
        self.assertIn("ABOUT_DOCUMENT", signal_statements)


def _qdrant_collection_client(
    collection_name: str,
    client: FakeQdrantClient,
    *,
    vector_size: int = 1,
) -> QdrantCollectionClient:
    return QdrantCollectionClient(
        config=QdrantCollectionConfig(
            collection_name=collection_name,
            vector_size=vector_size,
        ),
        settings=QdrantSettings(url="http://qdrant:6333"),
        client=client,
    )


def _chunk_projection() -> DocumentChunkVectorProjection:
    return DocumentChunkVectorProjection(
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        source_version="v1",
        content_digest="content-digest-1",
        index_input_digest="index-input-v1",
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        chunk_id="chunk-1",
        chunk_index=0,
        chunking_version="chunking-test-v1",
        text="startup evidence",
        text_hash="hash-1",
        start_offset=0,
        end_offset=16,
        embedding_model="test-embedding",
        embedding_version="test-v1",
        index_schema_version="schema-v1",
    )


def _document_projection() -> DocumentVectorProjection:
    return DocumentVectorProjection(
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        source_version="v1",
        content_digest="content-digest-1",
        index_input_digest="index-input-v1",
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        embedding_input="startup summary",
        embedding_input_hash="hash-1",
        embedding_model="test-embedding",
        embedding_version="test-v1",
        index_schema_version="schema-v1",
    )


def _signal_projection() -> DocumentSignalVectorProjection:
    return DocumentSignalVectorProjection(
        signal_id="signal-1",
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        signal_type="summary",
        signal_key="document-summary",
        source_version="v1",
        content_digest="content-digest-1",
        index_input_digest="index-input-v1",
        confidence=0.8,
        attributes={},
        evidence=(ProjectionSignalEvidence(chunk_id="chunk-1", quote="startup evidence"),),
        embedding_input="startup summary",
        embedding_input_hash="signal-hash-1",
        embedding_model="test-embedding",
        embedding_version="test-v1",
        index_schema_version="schema-v1",
    )


def _folder_signal_projection() -> FolderSignalVectorProjection:
    return FolderSignalVectorProjection(
        signal_id="folder-signal-1",
        tenant="tenant-1",
        folder_id="folder-1",
        signal_type="responsibility",
        signal_key="responsibility",
        source_version="folder-v1",
        index_input_digest="folder-signal-input-v1",
        attributes={"responsibility_score": 0.8},
        related_document_id="doc-2",
        confidence=0.9,
        evidence=({"reason": "document outlier"},),
        embedding_input="startup folder responsibility",
        embedding_input_hash="folder-signal-hash-1",
        embedding_model="test-embedding",
        embedding_version="test-v1",
        index_schema_version="schema-v1",
    )


def _signal_payload(*, owner_kind: str) -> dict[str, object]:
    if owner_kind == "folder":
        return {
            "kind": "signal",
            "signal_id": "folder-signal-1",
            "tenant": "tenant-1",
            "owner_kind": "folder",
            "document_type": None,
            "document_id": None,
            "folder_id": "folder-1",
            "signal_type": "responsibility",
            "signal_key": "responsibility",
            "text": "Folder responsibility",
            "source_version": "folder-v1",
            "content_digest": None,
            "index_input_digest": "folder-signal-input-v1",
            "attributes": {"responsibility_score": 0.8},
            "related_document_id": "doc-2",
            "evidence": [{"reason": "document outlier"}],
            "confidence": 0.9,
            "embedding_input_hash": "folder-signal-hash-1",
            "embedding_model": "embedding",
            "embedding_version": "v1",
            "index_schema_version": "schema-v1",
            "metadata": {},
        }
    return {
        "kind": "signal",
        "signal_id": "signal-1",
        "tenant": "tenant-1",
        "owner_kind": "document",
        "document_type": "document",
        "document_id": "doc-1",
        "folder_id": None,
        "signal_type": "summary",
        "signal_key": "document-summary",
        "text": "Document summary",
        "source_version": "v1",
        "content_digest": "content-digest-1",
        "index_input_digest": "index-input-v1",
        "attributes": {},
        "related_document_id": None,
        "evidence": [{"chunk_id": "chunk-1", "quote": "startup evidence"}],
        "confidence": 0.8,
        "embedding_input_hash": "signal-hash-1",
        "embedding_model": "embedding",
        "embedding_version": "v1",
        "index_schema_version": "schema-v1",
        "metadata": {},
    }


def _folder_projection() -> FolderVectorProjection:
    return FolderVectorProjection(
        tenant="tenant-1",
        folder_id="folder-1",
        source_version="folder-v1",
        index_input_digest="folder-input-v1",
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        embedding_input="Founding\n\n/Company/Founding\n\nstartup folder",
        embedding_input_hash="folder-hash-1",
        embedding_model="test-embedding",
        embedding_version="test-v1",
        index_schema_version="schema-v1",
    )


if __name__ == "__main__":
    unittest.main()
