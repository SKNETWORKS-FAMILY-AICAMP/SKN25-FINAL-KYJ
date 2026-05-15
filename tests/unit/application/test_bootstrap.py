from __future__ import annotations

import json
import os
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from fastapi.testclient import TestClient

from foldmind_ai_core.adapters.inbound.messaging.broker import BrokerMessage
from foldmind_ai_core.application.dto.llm import LLMMessage
from foldmind_ai_core.application.services.prompts import (
    PROMPT_ANSWER_GENERATION,
    PROMPT_DOCUMENT_PROFILING,
    PROMPT_DRAFT_GENERATION,
    PROMPT_IDEAS_EXPLORATION,
    PROMPT_SUMMARIZATION,
    PROMPT_WORKFLOW_PLANNING,
    TOKEN_ALLOWED_WORKFLOW_ACTION_TYPES,
    TOKEN_UNTRUSTED_CONTEXT_INSTRUCTION,
)
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
from foldmind_ai_core.application.workflows.artifacts.store import WorkflowArtifactStore
from foldmind_ai_core.bootstrap.container import (
    AICoreDependencies,
    AIProviderAdapters,
    RepositoryAdapter,
    build_ai_provider,
    build_app,
    build_configured_app,
    build_outbox_projection_repository_adapter,
    build_outbox_worker,
    build_prompt_repository,
    build_use_cases,
    default_prompt_root,
)
from foldmind_ai_core.bootstrap.settings import (
    AIProvider,
    APISettings,
    OutboxProjectionTarget,
    load_settings,
)
from foldmind_ai_core.domain.indexing.chunks import DocumentChunk
from foldmind_ai_core.domain.reference.folders import FolderVectorProjection
from foldmind_ai_core.domain.retrieval.queries import SearchScope
from foldmind_ai_core.domain.retrieval.results import (
    DocumentRetrievalResult,
    FolderRetrievalResult,
    RetrievalResult,
    RetrievedFolder,
)
from foldmind_ai_core.domain.workflow.tasks import TaskSnapshot
from foldmind_ai_core.shared.types import Vector

TEST_CHUNKING_VERSION = "chunking-test-v1"
TEST_EMBEDDING_MODEL = "embedding-test-model"
TEST_EMBEDDING_VERSION = "embedding-test-v1"
TEST_INDEX_SCHEMA_VERSION = "index-schema-test-v1"
TEST_PROFILE_VERSION = "profile-test-v1"
TEST_PROFILE_SCHEMA_VERSION = "profile-schema-test-v1"
TEST_PROFILE_PROMPT_VERSION = "document-profile-prompt-test-v1"


def make_chunk(chunk_id: str, text: str) -> DocumentChunk:
    return DocumentChunk(
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
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
    )


class FakeEmbeddingProvider:
    def embed_texts(self, texts: list[str]) -> list[Vector]:
        return [[float(len(text))] for text in texts]


class FakeDocumentVectorRepository:
    def __init__(self) -> None:
        self.chunk_upserted: list[DocumentChunk] = []
        self.keyword_upserted: list[DocumentChunk] = []
        self.deleted: list[str] = []

    def replace_document_chunks(
        self,
        *,
        document_id: str,
        chunks: tuple[DocumentChunk, ...],
        vectors: tuple[Vector, ...],
    ) -> None:
        self.chunk_upserted.extend(chunks)

    def upsert_keywords(self, chunks: tuple[DocumentChunk, ...]) -> None:
        self.keyword_upserted.extend(chunks)

    def delete_document_keywords(
        self,
        *,
        document_id: str,
    ) -> None:
        self.deleted.append(document_id)

    def upsert_document_vector(self, *, projection: object, vector: Vector) -> None:
        pass

    def delete_document_chunks(
        self,
        *,
        document_id: str,
    ) -> None:
        self.deleted.append(document_id)

    def delete_document_vector(
        self,
        *,
        document_id: str,
    ) -> None:
        self.deleted.append(document_id)

    def search_chunks(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[RetrievalResult]:
        return [RetrievalResult(chunk=make_chunk("doc-1:chunk:dense", "dense result"), score=0.9)]

    def search_keywords(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[RetrievalResult]:
        return [
            RetrievalResult(chunk=make_chunk("doc-1:chunk:keyword", "keyword result"), score=3.0)
        ]

    def search_documents(self, **kwargs: object) -> list[object]:
        return []


class FakeFolderVectorRepository:
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
        return [
            FolderRetrievalResult(
                folder=RetrievedFolder(
                    tenant=tenant,
                    folder_id="folder-1",
                    source_version="folder-v1",
                ),
                score=0.8,
                reason="Folder metadata is semantically close to the query.",
            )
        ]


class FakeGraphRepository:
    def __init__(self) -> None:
        self.relationships: list[object] = []
        self.concepts: list[object] = []
        self.folder_hierarchies: list[object] = []
        self.deleted_documents: list[str] = []
        self.deleted_folders: list[str] = []

    def replace_document_relationships(self, projection: object) -> None:
        self.relationships.append(projection)

    def replace_document_concepts(self, projection: object) -> None:
        self.concepts.append(projection)

    def replace_document_projection(
        self,
        *,
        relationships: object,
        concepts: object,
    ) -> None:
        self.replace_document_relationships(relationships)
        self.replace_document_concepts(concepts)

    def replace_folder_hierarchy(self, projection: object) -> None:
        self.folder_hierarchies.append(projection)

    def upsert_tag(self, projection: object) -> None:
        pass

    def document_ids_for_scope(self, *, tenant: str, scope: SearchScope) -> tuple[str, ...]:
        return scope.document_ids

    def folders_for_documents(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
    ) -> dict[str, tuple[RetrievedFolder, ...]]:
        return {}

    def delete_document(self, *, document_id: str) -> None:
        self.deleted_documents.append(document_id)

    def delete_folder(self, *, folder_id: str) -> None:
        self.deleted_folders.append(folder_id)

    def graph_search(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[DocumentRetrievalResult]:
        return []


def make_find_folders_use_case(
    *,
    embeddings: FakeEmbeddingProvider | None = None,
    documents: FakeDocumentVectorRepository | None = None,
    folders: FakeFolderVectorRepository | None = None,
    graph: FakeGraphRepository | None = None,
) -> FindFoldersUseCase:
    documents = documents or FakeDocumentVectorRepository()
    graph = graph or FakeGraphRepository()
    return FindFoldersUseCase(
        retrieval=FolderRetrievalService(
            embeddings=embeddings or FakeEmbeddingProvider(),
            chunk_vectors=documents,
            document_vectors=documents,
            folder_vectors=folders or FakeFolderVectorRepository(),
            graph=graph,
        ),
        scope_resolver=RelationshipScopeResolver(graph=graph),
    )


def make_recommend_folder_use_case(
    find_folders: FindFoldersUseCase | None = None,
) -> RecommendFolderUseCase:
    return RecommendFolderUseCase(
        find_folders=find_folders or make_find_folders_use_case(),
    )


class FakeLLM:
    def __init__(self) -> None:
        self.messages: list[LLMMessage] = []

    def generate(self, messages: list[LLMMessage]) -> str:
        self.messages = messages
        return "generated answer"


class FakePromptRepository:
    def get(self, name: str) -> str:
        prompts = {
            PROMPT_ANSWER_GENERATION: (
                f"Answer prompt {{{{{TOKEN_UNTRUSTED_CONTEXT_INSTRUCTION}}}}}"
            ),
            PROMPT_DRAFT_GENERATION: (
                f"Draft prompt {{{{{TOKEN_UNTRUSTED_CONTEXT_INSTRUCTION}}}}}"
            ),
            PROMPT_DOCUMENT_PROFILING: "Document profile prompt",
            PROMPT_IDEAS_EXPLORATION: (
                f"Ideas prompt {{{{{TOKEN_UNTRUSTED_CONTEXT_INSTRUCTION}}}}}"
            ),
            PROMPT_SUMMARIZATION: (
                f"Summary prompt {{{{{TOKEN_UNTRUSTED_CONTEXT_INSTRUCTION}}}}}"
            ),
            PROMPT_WORKFLOW_PLANNING: (
                f"Plan prompt {{{{{TOKEN_ALLOWED_WORKFLOW_ACTION_TYPES}}}}}"
            ),
        }
        return prompts[name]


class FakeTaskRepository:
    def __init__(self) -> None:
        self.items: dict[str, TaskSnapshot] = {}

    def create(self, snapshot: TaskSnapshot) -> None:
        self.items[snapshot.task_id] = snapshot

    def get(self, *, task_id: str) -> TaskSnapshot | None:
        return self.items.get(task_id)

    def get_by_request_id(self, *, task_request_id: str) -> TaskSnapshot | None:
        return next(
            (
                snapshot
                for snapshot in self.items.values()
                for request in snapshot.requests
                if request.task_request_id == task_request_id
            ),
            None,
        )

    def get_by_action_id(self, *, action_id: str) -> TaskSnapshot | None:
        return next(
            (
                snapshot
                for snapshot in self.items.values()
                for action in snapshot.host_actions
                if action.action_id == action_id
            ),
            None,
        )

    def save(self, snapshot: TaskSnapshot) -> None:
        self.items[snapshot.task_id] = snapshot


class FakeProfileRepository:
    def __init__(self) -> None:
        self.items: dict[str, object] = {}
        self.deleted: list[str] = []

    def upsert(self, profile: object) -> None:
        self.items[str(profile.document_id)] = profile

    def get_document_profile(
        self,
        *,
        document_id: str,
    ) -> object | None:
        return self.items.get(document_id)

    def delete_document_profile(
        self,
        *,
        document_id: str,
    ) -> None:
        self.deleted.append(document_id)


class FakeIndexingTransaction:
    def __init__(self) -> None:
        self.document_profiles: dict[str, object] = {}
        self.deleted_documents: list[str] = []
        self.events: list[object] = []

    def upsert_document_profile(self, profile: object) -> None:
        self.document_profiles[str(profile.document_id)] = profile

    def delete_document_profile(self, *, document_id: str) -> None:
        self.deleted_documents.append(document_id)

    def append_outbox_event(self, event: object) -> None:
        self.events.append(event)


class FakeIndexingUnitOfWork:
    def __init__(self) -> None:
        self.tx = FakeIndexingTransaction()

    @contextmanager
    def transaction(self):
        yield self.tx


class FakeBrokerConsumer:
    def __init__(self, messages: list[BrokerMessage]) -> None:
        self.messages = messages
        self.committed: list[BrokerMessage] = []
        self.closed = False

    def poll(self, timeout_seconds: float) -> BrokerMessage | None:
        if not self.messages:
            return None
        return self.messages.pop(0)

    def commit(self, message: BrokerMessage) -> None:
        self.committed.append(message)

    def close(self) -> None:
        self.closed = True


class FakeDlqProducer:
    def __init__(self) -> None:
        self.published: list[dict[str, object]] = []
        self.closed = False

    def publish(
        self,
        *,
        topic: str,
        key: bytes | str | None,
        value: dict[str, object],
        headers: tuple[tuple[str, bytes | str | None], ...] = (),
    ) -> None:
        self.published.append(value)

    def close(self) -> None:
        self.closed = True


class FakeOutboxFreshnessStore:
    def latest_sequence_for(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
    ) -> int | None:
        return 1


def make_repository_adapter(
    *,
    document_vectors: FakeDocumentVectorRepository | None = None,
    graph: FakeGraphRepository | None = None,
) -> RepositoryAdapter:
    document_vectors = document_vectors or FakeDocumentVectorRepository()
    return RepositoryAdapter(
        task_repository=FakeTaskRepository(),
        profile_repository=FakeProfileRepository(),
        indexing_uow=FakeIndexingUnitOfWork(),
        chunk_vectors=document_vectors,
        document_vectors=document_vectors,
        folder_vectors=FakeFolderVectorRepository(),
        graph=graph or FakeGraphRepository(),
        keyword_repository=document_vectors,
    )


class BootstrapTests(unittest.TestCase):
    def test_api_settings_can_be_loaded_from_environment(self) -> None:
        keys = (
            "FOLDMIND_API_TITLE",
            "FOLDMIND_API_VERSION",
            "FOLDMIND_CORS_ORIGINS",
            "FOLDMIND_CORS_ALLOW_CREDENTIALS",
            "POSTGRES_DSN",
            "QDRANT_URL",
            "QDRANT_API_KEY",
            "NEO4J_URI",
            "NEO4J_USER",
            "NEO4J_PASSWORD",
            "AI_PROVIDER",
            "OPENAI_API_KEY",
            "OPENAI_BASE_URL",
            "LLM_MODEL",
            "EMBEDDING_MODEL",
            "EMBEDDING_VERSION",
            "CHUNKING_VERSION",
            "INDEX_SCHEMA_VERSION",
            "PROFILE_VERSION",
            "PROFILE_SCHEMA_VERSION",
            "DOCUMENT_PROFILE_PROMPT_VERSION",
            "EMBEDDING_DIMENSIONS",
            "OPENAI_TIMEOUT_SECONDS",
            "OPENAI_MAX_RETRIES",
            "KAFKA_BOOTSTRAP_SERVERS",
            "KAFKA_OUTBOX_TOPIC",
            "OUTBOX_PROJECTION_TARGET",
            "KAFKA_DLQ_TOPIC",
            "KAFKA_MAX_RETRIES",
            "KAFKA_RETRY_BACKOFF_SECONDS",
        )
        previous = {key: os.environ.get(key) for key in keys}
        try:
            os.environ["FOLDMIND_API_TITLE"] = "Custom FoldMind"
            os.environ["FOLDMIND_API_VERSION"] = "9.9.9"
            os.environ["FOLDMIND_CORS_ORIGINS"] = "http://localhost:3000, https://app.test"
            os.environ["FOLDMIND_CORS_ALLOW_CREDENTIALS"] = "false"
            os.environ["POSTGRES_DSN"] = "postgresql://user:pass@postgres:5432/core"
            os.environ["QDRANT_URL"] = "http://qdrant:6333"
            os.environ["QDRANT_API_KEY"] = "qdrant-secret"
            os.environ["NEO4J_URI"] = "bolt://neo4j:7687"
            os.environ["NEO4J_USER"] = "neo4j"
            os.environ["NEO4J_PASSWORD"] = "neo4j-secret"
            os.environ["AI_PROVIDER"] = "openai"
            os.environ["OPENAI_API_KEY"] = "openai-secret"
            os.environ["OPENAI_BASE_URL"] = "https://api.openai.test/v1"
            os.environ["LLM_MODEL"] = "gpt-5-mini"
            os.environ["EMBEDDING_MODEL"] = "text-embedding-3-large"
            os.environ["EMBEDDING_VERSION"] = "embedding-prod-v1"
            os.environ["CHUNKING_VERSION"] = "chunking-prod-v1"
            os.environ["INDEX_SCHEMA_VERSION"] = "index-schema-prod-v1"
            os.environ["PROFILE_VERSION"] = "profile-prod-v1"
            os.environ["PROFILE_SCHEMA_VERSION"] = "profile-schema-prod-v1"
            os.environ["DOCUMENT_PROFILE_PROMPT_VERSION"] = "profile-prompt-prod-v1"
            os.environ["EMBEDDING_DIMENSIONS"] = "1024"
            os.environ["OPENAI_TIMEOUT_SECONDS"] = "45"
            os.environ["OPENAI_MAX_RETRIES"] = "4"
            os.environ["KAFKA_BOOTSTRAP_SERVERS"] = "kafka:9092"
            os.environ["KAFKA_OUTBOX_TOPIC"] = "indexing-events"
            os.environ["OUTBOX_PROJECTION_TARGET"] = "neo4j-graph"
            os.environ["KAFKA_DLQ_TOPIC"] = "indexing-events.dlq"
            os.environ["KAFKA_MAX_RETRIES"] = "5"
            os.environ["KAFKA_RETRY_BACKOFF_SECONDS"] = "2.5"

            settings = APISettings()

            self.assertEqual(settings.title, "Custom FoldMind")
            self.assertEqual(settings.version, "9.9.9")
            self.assertEqual(
                settings.cors_origins,
                ("http://localhost:3000", "https://app.test"),
            )
            self.assertFalse(settings.cors_allow_credentials)
            self.assertEqual(settings.postgres_dsn, "postgresql://user:pass@postgres:5432/core")
            self.assertEqual(settings.qdrant_url, "http://qdrant:6333")
            self.assertEqual(settings.qdrant_api_key_value, "qdrant-secret")
            self.assertEqual(settings.neo4j_user, "neo4j")
            self.assertEqual(settings.neo4j_password_value, "neo4j-secret")
            self.assertEqual(settings.ai_provider, AIProvider.OPENAI)
            self.assertEqual(settings.openai_api_key_value, "openai-secret")
            self.assertEqual(settings.openai_base_url, "https://api.openai.test/v1")
            self.assertEqual(settings.llm_model, "gpt-5-mini")
            self.assertEqual(settings.embedding_model, "text-embedding-3-large")
            self.assertEqual(settings.embedding_version, "embedding-prod-v1")
            self.assertEqual(settings.chunking_version, "chunking-prod-v1")
            self.assertEqual(settings.index_schema_version, "index-schema-prod-v1")
            self.assertEqual(settings.profile_version, "profile-prod-v1")
            self.assertEqual(settings.profile_schema_version, "profile-schema-prod-v1")
            self.assertEqual(
                settings.document_profile_prompt_version,
                "profile-prompt-prod-v1",
            )
            self.assertEqual(settings.embedding_dimensions, 1024)
            self.assertEqual(settings.openai_timeout_seconds, 45)
            self.assertEqual(settings.openai_max_retries, 4)
            self.assertEqual(settings.kafka_bootstrap_servers, "kafka:9092")
            self.assertEqual(settings.kafka_outbox_topic, "indexing-events")
            self.assertEqual(
                settings.outbox_projection_target,
                OutboxProjectionTarget.NEO4J_GRAPH,
            )
            self.assertEqual(settings.kafka_dlq_topic, "indexing-events.dlq")
            self.assertEqual(settings.kafka_max_retries, 5)
            self.assertEqual(settings.kafka_retry_backoff_seconds, 2.5)
            self.assertIn("cors_origins", APISettings.model_fields)
            self.assertNotIn("cors_origins_csv", APISettings.model_fields)
            self.assertNotIn("kafka_consumer_group", APISettings.model_fields)
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_settings_loads_local_external_and_hybrid_env_files(self) -> None:
        local = load_settings("examples/env/local.env")
        external = load_settings("examples/env/external.env")
        hybrid = load_settings("examples/env/hybrid.env")

        self.assertEqual(local.postgres_dsn, "postgresql://foldmind:foldmind@postgres:5432/foldmind_ai_core")
        self.assertEqual(local.qdrant_url, "http://qdrant:6333")
        self.assertEqual(local.neo4j_uri, "bolt://neo4j:7687")
        self.assertEqual(local.ai_provider, AIProvider.OPENAI)
        self.assertEqual(local.openai_api_key_value, "REPLACE_ME")
        self.assertEqual(local.llm_model, "gpt-4.1-mini")
        self.assertEqual(local.embedding_dimensions, 1536)
        self.assertEqual(local.profile_version, "profile-v1")
        self.assertEqual(local.profile_schema_version, "profile-schema-v1")
        self.assertEqual(local.document_profile_prompt_version, "document-profile-prompt-v1")
        self.assertEqual(local.kafka_bootstrap_servers, "kafka:9092")
        self.assertEqual(
            local.outbox_projection_target,
            OutboxProjectionTarget.NEO4J_GRAPH,
        )
        self.assertEqual(local.kafka_dlq_topic, "indexing-events.dlq")
        self.assertEqual(external.qdrant_api_key_value, "REPLACE_ME")
        self.assertEqual(external.kafka_outbox_topic, "indexing-events")
        self.assertEqual(
            external.outbox_projection_target,
            OutboxProjectionTarget.NEO4J_GRAPH,
        )
        self.assertEqual(hybrid.qdrant_url, "https://REPLACE_ME.cloud.qdrant.io")
        self.assertEqual(hybrid.neo4j_uri, "bolt://host.docker.internal:7687")
        self.assertEqual(hybrid.kafka_bootstrap_servers, "host.docker.internal:9092")
        self.assertEqual(
            hybrid.outbox_projection_target,
            OutboxProjectionTarget.NEO4J_GRAPH,
        )
        expected_groups = {
            OutboxProjectionTarget.QDRANT_DOCUMENT_CHUNKS: (
                "foldmind-ai-core-outbox-qdrant-document-chunks"
            ),
            OutboxProjectionTarget.QDRANT_DOCUMENTS: (
                "foldmind-ai-core-outbox-qdrant-documents"
            ),
            OutboxProjectionTarget.QDRANT_FOLDERS: (
                "foldmind-ai-core-outbox-qdrant-folders"
            ),
            OutboxProjectionTarget.NEO4J_GRAPH: "foldmind-ai-core-outbox-neo4j-graph",
        }
        for target, expected_group in expected_groups.items():
            with self.subTest(target=target):
                self.assertEqual(
                    hybrid.outbox_consumer_group_for_projection(target),
                    expected_group,
                )

    def test_settings_can_validate_storage_requirements(self) -> None:
        settings = APISettings(
            qdrant_url=None,
        )

        with self.assertRaisesRegex(ValueError, "QDRANT_URL is required"):
            settings.require_configured_storage()

    def test_standard_storage_requires_graph_database_credentials(self) -> None:
        settings = APISettings(
            qdrant_url="http://qdrant:6333",
            postgres_dsn="postgresql://user:pass@postgres:5432/core",
            neo4j_uri=None,
            neo4j_user=None,
            neo4j_password=None,
        )

        with self.assertRaisesRegex(ValueError, "NEO4J_URI"):
            settings.require_configured_storage()

    def test_bootstrap_wires_dependencies_into_app(self) -> None:
        document_vectors = FakeDocumentVectorRepository()
        llm = FakeLLM()
        graph = FakeGraphRepository()
        dependencies = AICoreDependencies(
            ai=AIProviderAdapters(
                llm=llm,
                embeddings=FakeEmbeddingProvider(),
            ),
            repositories=make_repository_adapter(
                document_vectors=document_vectors,
                graph=graph,
            ),
            prompt_repository=FakePromptRepository(),
        )

        settings = APISettings(
            allow_in_memory_workflow_checkpoint=True,
            embedding_model=TEST_EMBEDDING_MODEL,
            chunking_version=TEST_CHUNKING_VERSION,
            embedding_version=TEST_EMBEDDING_VERSION,
            index_schema_version=TEST_INDEX_SCHEMA_VERSION,
            profile_version=TEST_PROFILE_VERSION,
            profile_schema_version=TEST_PROFILE_SCHEMA_VERSION,
            document_profile_prompt_version=TEST_PROFILE_PROMPT_VERSION,
        )
        use_cases = build_use_cases(dependencies, settings=settings)
        app = build_app(dependencies, settings=settings)
        client = TestClient(app)

        index_response = client.post(
            "/indexing/documents",
            json={
                "document": {
                    "tenant": "tenant-1",
                    "document_type": "document",
                    "document_id": "11111111-1111-4111-8111-111111111111",
                    "source_version": "v1",
                    "title": "Meeting notes",
                    "body": "Prepare next meeting",
                }
            },
        )
        answer_response = client.post(
            "/retrieval/answer",
            json={
                "query": {
                    "text": "What happened?",
                    "request_context": {"tenant": "tenant-1"},
                }
            },
        )

        self.assertIs(
            use_cases.answer_question.find_documents,
            use_cases.search_documents,
        )
        self.assertEqual(index_response.status_code, 200)
        outbox_events = dependencies.repositories.indexing_uow.tx.events
        self.assertEqual(len(document_vectors.chunk_upserted), 0)
        self.assertEqual(len(document_vectors.keyword_upserted), 0)
        self.assertEqual(len(graph.relationships), 0)
        self.assertEqual(len(graph.concepts), 0)
        self.assertEqual(len(outbox_events), 1)
        self.assertEqual(outbox_events[0].event_type, "DOCUMENT_INDEXED")
        self.assertEqual(answer_response.status_code, 200)
        self.assertEqual(answer_response.json()["text"], "generated answer")
        self.assertGreater(len(answer_response.json()["citations"]), 0)
        self.assertGreater(len(llm.messages), 0)
        self.assertIn("Answer prompt", llm.messages[0].content)

    def test_outbox_worker_factory_wires_projection_use_cases_and_runtime(self) -> None:
        document_vectors = FakeDocumentVectorRepository()
        graph = FakeGraphRepository()
        repositories = make_repository_adapter(
            document_vectors=document_vectors,
            graph=graph,
        )
        message = BrokerMessage(
            key=b"DOCUMENT:doc-1",
            topic="indexing-events",
            partition=0,
            offset=1,
            value=json.dumps(
                {
                    "id": "11111111-1111-4111-8111-111111111111",
                    "sequence": 1,
                    "event_key": "DOCUMENT:doc-1",
                    "aggregate_type": "DOCUMENT",
                    "aggregate_id": "doc-1",
                    "event_type": "DOCUMENT_DELETED",
                    "source_version": "v1",
                    "event_schema_version": "1",
                    "payload": {
                        "tenant": "tenant-1",
                        "document_id": "doc-1",
                        "source_version": "v1",
                    },
                }
            ).encode("utf-8"),
        )
        consumer = FakeBrokerConsumer([message])
        dlq = FakeDlqProducer()
        settings = APISettings(
            allow_in_memory_workflow_checkpoint=True,
            kafka_bootstrap_servers="kafka:9092",
            outbox_projection_target=OutboxProjectionTarget.NEO4J_GRAPH,
            kafka_max_retries=0,
            embedding_model=TEST_EMBEDDING_MODEL,
            chunking_version=TEST_CHUNKING_VERSION,
            embedding_version=TEST_EMBEDDING_VERSION,
            index_schema_version=TEST_INDEX_SCHEMA_VERSION,
            profile_version=TEST_PROFILE_VERSION,
            profile_schema_version=TEST_PROFILE_SCHEMA_VERSION,
            document_profile_prompt_version=TEST_PROFILE_PROMPT_VERSION,
        )
        worker = build_outbox_worker(
            settings=settings,
            repository_adapter=repositories,
            kafka_consumer=consumer,
            dlq_producer=dlq,
            outbox_freshness_store=FakeOutboxFreshnessStore(),
        )

        handled = worker.run_once()

        self.assertTrue(handled)
        self.assertEqual(consumer.committed, [message])
        self.assertEqual(document_vectors.deleted, [])
        self.assertEqual(graph.deleted_documents, ["doc-1"])
        self.assertEqual(dlq.published, [])

    def test_outbox_worker_factory_wires_one_projection_target_per_worker(self) -> None:
        document_vectors = FakeDocumentVectorRepository()
        graph = FakeGraphRepository()
        repositories = make_repository_adapter(
            document_vectors=document_vectors,
            graph=graph,
        )
        message = BrokerMessage(
            key=b"DOCUMENT:doc-1",
            topic="indexing-events",
            partition=0,
            offset=1,
            value=json.dumps(
                {
                    "id": "11111111-1111-4111-8111-111111111111",
                    "sequence": 1,
                    "event_key": "DOCUMENT:doc-1",
                    "aggregate_type": "DOCUMENT",
                    "aggregate_id": "doc-1",
                    "event_type": "DOCUMENT_DELETED",
                    "source_version": "v1",
                    "event_schema_version": "1",
                    "payload": {
                        "tenant": "tenant-1",
                        "document_id": "doc-1",
                        "source_version": "v1",
                    },
                }
            ).encode("utf-8"),
        )
        consumer = FakeBrokerConsumer([message])
        dlq = FakeDlqProducer()
        settings = APISettings(
            allow_in_memory_workflow_checkpoint=True,
            kafka_bootstrap_servers="kafka:9092",
            outbox_projection_target=OutboxProjectionTarget.QDRANT_DOCUMENT_CHUNKS,
            kafka_max_retries=0,
            embedding_model=TEST_EMBEDDING_MODEL,
            chunking_version=TEST_CHUNKING_VERSION,
            embedding_version=TEST_EMBEDDING_VERSION,
            index_schema_version=TEST_INDEX_SCHEMA_VERSION,
            profile_version=TEST_PROFILE_VERSION,
            profile_schema_version=TEST_PROFILE_SCHEMA_VERSION,
            document_profile_prompt_version=TEST_PROFILE_PROMPT_VERSION,
        )
        worker = build_outbox_worker(
            settings=settings,
            repository_adapter=repositories,
            ai_provider_adapters=AIProviderAdapters(
                llm=FakeLLM(),
                embeddings=FakeEmbeddingProvider(),
            ),
            kafka_consumer=consumer,
            dlq_producer=dlq,
            outbox_freshness_store=FakeOutboxFreshnessStore(),
        )

        handled = worker.run_once()

        self.assertTrue(handled)
        self.assertEqual(consumer.committed, [message])
        self.assertEqual(document_vectors.deleted, ["doc-1"])
        self.assertEqual(graph.deleted_documents, [])
        self.assertEqual(dlq.published, [])

    def test_outbox_projection_repository_factory_builds_only_target_storage(self) -> None:
        settings = APISettings(
            qdrant_url="http://qdrant:6333",
            neo4j_uri="bolt://neo4j:7687",
            neo4j_user="neo4j",
            neo4j_password="secret",
        )
        graph = FakeGraphRepository()
        document_vectors = FakeDocumentVectorRepository()
        folder_vectors = FakeFolderVectorRepository()

        with (
            patch(
                "foldmind_ai_core.bootstrap.container.repositories._build_neo4j_repository",
                return_value=graph,
            ) as build_neo4j,
            patch(
                "foldmind_ai_core.bootstrap.container.repositories."
                "_build_qdrant_document_chunk_vector_repository",
                return_value=document_vectors,
            ) as build_chunk_vectors,
            patch(
                "foldmind_ai_core.bootstrap.container.repositories."
                "_build_qdrant_document_vector_repository",
                return_value=document_vectors,
            ) as build_document_vectors,
            patch(
                "foldmind_ai_core.bootstrap.container.repositories."
                "_build_qdrant_folder_vector_repository",
                return_value=folder_vectors,
            ) as build_folder_vectors,
        ):
            graph_repositories = build_outbox_projection_repository_adapter(
                settings,
                target=OutboxProjectionTarget.NEO4J_GRAPH,
            )
            qdrant_repositories = build_outbox_projection_repository_adapter(
                settings,
                target=OutboxProjectionTarget.QDRANT_DOCUMENTS,
            )

        self.assertIs(graph_repositories.graph, graph)
        self.assertIsNone(graph_repositories.document_vectors)
        self.assertIs(qdrant_repositories.document_vectors, document_vectors)
        self.assertIsNone(qdrant_repositories.chunk_vectors)
        self.assertIsNone(qdrant_repositories.folder_vectors)
        self.assertIsNone(qdrant_repositories.graph)
        self.assertEqual(build_neo4j.call_count, 1)
        self.assertEqual(build_chunk_vectors.call_count, 0)
        self.assertEqual(build_document_vectors.call_count, 1)
        self.assertEqual(build_folder_vectors.call_count, 0)

    def test_configured_app_wires_storage_ai_and_packaged_prompts(self) -> None:
        document_vectors = FakeDocumentVectorRepository()
        llm = FakeLLM()
        repositories = make_repository_adapter(document_vectors=document_vectors)
        ai_adapters = AIProviderAdapters(
            llm=llm,
            embeddings=FakeEmbeddingProvider(),
        )
        settings = APISettings(
            allow_in_memory_workflow_checkpoint=True,
            prompt_root=str(default_prompt_root()),
            embedding_model=TEST_EMBEDDING_MODEL,
            chunking_version=TEST_CHUNKING_VERSION,
            embedding_version=TEST_EMBEDDING_VERSION,
            index_schema_version=TEST_INDEX_SCHEMA_VERSION,
            profile_version=TEST_PROFILE_VERSION,
            profile_schema_version=TEST_PROFILE_SCHEMA_VERSION,
            document_profile_prompt_version=TEST_PROFILE_PROMPT_VERSION,
        )

        app = build_configured_app(
            settings=settings,
            repository_adapter=repositories,
            ai_provider_adapters=ai_adapters,
        )
        client = TestClient(app)

        paths = {route.path for route in app.routes}
        response = client.post(
            "/retrieval/answer",
            json={
                "query": {
                    "text": "What happened?",
                    "request_context": {"tenant": "tenant-1"},
                }
            },
        )

        self.assertIn("/health", paths)
        self.assertIn("/retrieval/search", paths)
        self.assertIn("/indexing/documents", paths)
        self.assertIn("/tasks", paths)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Answer Generation", llm.messages[0].content)

    def test_standard_storage_requires_task_repository_dsn(self) -> None:
        settings = APISettings(
            qdrant_url="http://qdrant:6333",
            postgres_dsn=None,
        )

        with self.assertRaisesRegex(ValueError, "POSTGRES_DSN is required"):
            settings.require_configured_storage()

    def test_openai_requires_api_key_and_rejects_unsupported_provider(self) -> None:
        with self.assertRaisesRegex(ValueError, "OPENAI_API_KEY is required"):
            build_ai_provider(APISettings(openai_api_key=None))

        settings = APISettings(
            openai_api_key="openai-secret",
            embedding_model=TEST_EMBEDDING_MODEL,
        )
        settings.ai_provider = "unsupported"  # type: ignore[assignment]
        with self.assertRaisesRegex(RuntimeError, "Unsupported AI_PROVIDER"):
            build_ai_provider(settings)

    def test_default_prompt_repository_uses_packaged_prompt_resources(self) -> None:
        repository = build_prompt_repository(APISettings())

        self.assertIn("Answer Generation", repository.get(PROMPT_ANSWER_GENERATION))

    def test_workflow_artifact_store_has_no_external_use_case_dependencies(self) -> None:
        store = WorkflowArtifactStore()

        self.assertFalse(hasattr(store, "find_documents"))
        self.assertFalse(hasattr(store, "find_folders"))


if __name__ == "__main__":
    unittest.main()
