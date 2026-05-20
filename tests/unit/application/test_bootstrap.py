from __future__ import annotations

import json
import os
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from fastapi.testclient import TestClient

from foldmind_ai_core.adapters.inbound.messaging.broker import BrokerMessage
from foldmind_ai_core.bootstrap.configured_app import (
    build_app,
    build_configured_app,
)
from foldmind_ai_core.bootstrap.container.dependencies import (
    AICapabilities,
    ApplicationDependencies,
    ApplicationStorage,
)
from foldmind_ai_core.bootstrap.container.outbox import build_outbox_worker
from foldmind_ai_core.bootstrap.container.providers import (
    build_ai_capabilities,
    build_prompt_store,
    default_prompt_root,
)
from foldmind_ai_core.bootstrap.container.storage import (
    build_outbox_projection_storage,
)
from foldmind_ai_core.bootstrap.container.use_cases import (
    build_use_cases,
)
from foldmind_ai_core.bootstrap.settings import (
    AIProvider,
    APISettings,
    OutboxProjectionTarget,
    load_settings,
)
from foldmind_ai_core.core.application.models.indexing import (
    DeletedDocumentIdentity,
    DeletedFolderIdentity,
)
from foldmind_ai_core.core.application.models.llm import LLMMessage
from foldmind_ai_core.core.application.projections.vector import FolderVectorProjection
from foldmind_ai_core.core.application.queries.retrieval import SearchScope
from foldmind_ai_core.core.application.services.folder_retrieval_service import (
    FolderRetrievalService,
)
from foldmind_ai_core.core.application.services.prompts import (
    PROMPT_ANSWER_GENERATION,
    PROMPT_CHUNK_RELEVANCE_FILTERING,
    PROMPT_DOCUMENT_PROFILING,
    PROMPT_DRAFT_GENERATION,
    PROMPT_IDEAS_EXPLORATION,
    PROMPT_SUMMARIZATION,
    PROMPT_WORKFLOW_PLANNING,
    TOKEN_ALLOWED_WORKFLOW_ACTION_TYPES,
    TOKEN_UNTRUSTED_CONTEXT_INSTRUCTION,
)
from foldmind_ai_core.core.application.services.relationship_scope_resolver import (
    RelationshipScopeResolver,
)
from foldmind_ai_core.core.application.use_cases.recommendation.find_folders import (
    FindFoldersUseCase,
)
from foldmind_ai_core.core.application.use_cases.recommendation.recommend_folder import (
    RecommendFolderUseCase,
)
from foldmind_ai_core.core.application.workflows.artifacts.registry import (
    WorkflowArtifactRegistry,
)
from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.reference.documents import SourceDocument
from foldmind_ai_core.core.domain.models.retrieval.results import (
    DocumentRetrievalResult,
    FolderRetrievalResult,
    RetrievalResult,
    RetrievedFolder,
)
from foldmind_ai_core.core.domain.models.workflow.tasks import TaskSnapshot
from foldmind_ai_core.shared.types import Vector

TEST_CHUNKING_VERSION = "chunking-test-v1"
TEST_EMBEDDING_MODEL = "embedding-test-model"
TEST_EMBEDDING_VERSION = "embedding-test-v1"
TEST_INDEX_SCHEMA_VERSION = "index-schema-test-v1"
TEST_PROFILE_PROMPT_VERSION = "document-profile-prompt-test-v1"


def make_chunk(chunk_id: str, text: str) -> DocumentChunk:
    return DocumentChunk(
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        source_version="v1",
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
    )


class FakeEmbeddingProvider:
    def embed_texts(self, texts: list[str]) -> list[Vector]:
        return [[float(len(text))] for text in texts]


class FakeDocumentVectorStore:
    def __init__(self) -> None:
        self.chunk_upserted: list[DocumentChunk] = []
        self.document_upserted: list[object] = []
        self.deleted: list[str] = []

    def replace_document_chunks(
        self,
        *,
        tenant: str,
        document_id: str,
        chunks: tuple[DocumentChunk, ...],
        vectors: tuple[Vector, ...],
    ) -> None:
        self.chunk_upserted.extend(chunks)

    def upsert_document_vector(self, *, projection: object, vector: Vector) -> None:
        self.document_upserted.append(projection)

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

    def search_documents(self, **kwargs: object) -> list[object]:
        return []


class FakeFolderVectorStore:
    def __init__(self) -> None:
        self.upserted: list[FolderVectorProjection] = []
        self.deleted: list[str] = []

    def upsert_folder_vector(
        self,
        *,
        projection: FolderVectorProjection,
        vector: Vector,
    ) -> None:
        self.upserted.append(projection)

    def delete_folder_vector(self, *, folder_id: str) -> None:
        self.deleted.append(folder_id)

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
                    created_at="2026-05-01T10:00:00+09:00",
                    updated_at="2026-05-02T11:00:00+09:00",
                ),
                score=0.8,
                reason="Folder metadata is semantically close to the query.",
            )
        ]


class FakeSignalVectorStore:
    def __init__(self) -> None:
        self.upserted: list[object] = []
        self.deleted: list[str] = []

    def replace_document_signals(
        self,
        *,
        tenant: str,
        document_id: str,
        signals: tuple[object, ...],
        vectors: tuple[Vector, ...],
    ) -> None:
        self.upserted.extend(signals)

    def delete_document_signals(
        self,
        *,
        document_id: str,
    ) -> None:
        self.deleted.append(document_id)

    def replace_folder_signals(
        self,
        *,
        tenant: str,
        folder_id: str,
        signals: tuple[object, ...],
        vectors: tuple[Vector, ...],
    ) -> None:
        self.upserted.extend(signals)

    def delete_folder_signals(
        self,
        *,
        folder_id: str,
    ) -> None:
        self.deleted.append(folder_id)

    def search_signals(self, **kwargs: object) -> list[object]:
        return []


class FakeGraphStore:
    def __init__(self) -> None:
        self.relationships: list[object] = []
        self.signals: list[object] = []
        self.folder_hierarchies: list[object] = []
        self.deleted_documents: list[str] = []
        self.deleted_folder_signals: list[str] = []
        self.deleted_folders: list[str] = []

    def replace_document_projection(
        self,
        *,
        relationships: object,
        signals: object,
    ) -> None:
        self.relationships.append(relationships)
        self.signals.append(signals)

    def replace_document_folder_relations(self, *, projection: object) -> None:
        self.relationships.append(projection)

    def replace_folder_hierarchy(self, projection: object) -> None:
        self.folder_hierarchies.append(projection)

    def replace_folder_projection(self, *, relationships: object, signals: object) -> None:
        self.folder_hierarchies.append(relationships)
        self.signals.append(signals)

    def document_ids_for_scope(self, *, tenant: str, scope: SearchScope) -> tuple[str, ...]:
        return scope.document_ids

    def folders_for_documents(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
    ) -> dict[str, tuple[RetrievedFolder, ...]]:
        return {}

    def delete_document(
        self,
        *,
        document_id: str,
    ) -> None:
        self.deleted_documents.append(document_id)

    def delete_folder_signals(self, *, folder_id: str) -> None:
        self.deleted_folder_signals.append(folder_id)

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


class FakeIndexedDocumentSourceRepository:
    def get_current_document_source(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> SourceDocument | None:
        return None

    def get_current_document_folder_ids(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> tuple[str, ...]:
        return ()


def make_find_folders_use_case(
    *,
    embeddings: FakeEmbeddingProvider | None = None,
    documents: FakeDocumentVectorStore | None = None,
    folders: FakeFolderVectorStore | None = None,
    graph: FakeGraphStore | None = None,
) -> FindFoldersUseCase:
    documents = documents or FakeDocumentVectorStore()
    graph = graph or FakeGraphStore()
    return FindFoldersUseCase(
        retrieval=FolderRetrievalService(
            embeddings=embeddings or FakeEmbeddingProvider(),
            chunk_vectors=documents,
            document_vectors=documents,
            folder_vectors=folders or FakeFolderVectorStore(),
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


class FakeLLMProvider:
    def __init__(self) -> None:
        self.messages: list[LLMMessage] = []

    def generate(self, messages: list[LLMMessage]) -> str:
        self.messages = messages
        system_prompt = messages[0].content
        if (
            "Document profile prompt" in system_prompt
            or "structured DocumentProfile" in system_prompt
        ):
            payload = json.loads(messages[1].content)
            chunk = payload["chunks"][0]
            chunk_id = chunk["chunk_id"]
            quote = chunk["text"]
            evidence_json = (
                f'"evidence":[{{"chunk_id":{json.dumps(chunk_id)},'
                f'"quote":{json.dumps(quote)}}}],'
            )
            return (
                '{"signals":['
                '{"type":"summary","text":"Meeting preparation notes",'
                '"attributes":{},'
                f"{evidence_json}"
                '"confidence":0.8},'
                '{"type":"concept","text":"meeting","attributes":{"label":"meeting"},'
                f"{evidence_json}"
                '"confidence":0.8}'
                ']}'
            )
        if (
            "Relevance prompt" in system_prompt
            or "filter retrieved chunks" in system_prompt
        ):
            return (
                '{"results":[{"chunk_id":"doc-1:chunk:dense",'
                '"relevant":true,'
                '"confidence":0.9}]}'
            )
        return "generated answer"


class FakePromptStore:
    def get(self, name: str) -> str:
        prompts = {
            PROMPT_ANSWER_GENERATION: (
                f"Answer prompt {{{{{TOKEN_UNTRUSTED_CONTEXT_INSTRUCTION}}}}}"
            ),
            PROMPT_DRAFT_GENERATION: (
                f"Draft prompt {{{{{TOKEN_UNTRUSTED_CONTEXT_INSTRUCTION}}}}}"
            ),
            PROMPT_CHUNK_RELEVANCE_FILTERING: "Relevance prompt",
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

    def get_by_input_id(self, *, task_input_id: str) -> TaskSnapshot | None:
        return next(
            (
                snapshot
                for snapshot in self.items.values()
                for request in snapshot.inputs
                if request.task_input_id == task_input_id
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


class FakeIndexingTransaction:
    def __init__(self) -> None:
        self.document_indexes: dict[str, object] = {}
        self.deleted_documents: list[str] = []
        self.events: list[object] = []

    def upsert_document_index(
        self,
        *,
        document: object,
        chunks: tuple[object, ...],
        profile: object,
        signals: tuple[object, ...],
    ) -> None:
        self.document_indexes[str(profile.document_id)] = profile

    def replace_document_folder_relation_snapshot(self, *, snapshot: object) -> bool:
        return True

    def mark_document_deleted(
        self,
        *,
        document_id: str,
    ) -> DeletedDocumentIdentity:
        self.deleted_documents.append(document_id)
        return DeletedDocumentIdentity(
            tenant="tenant-1",
            document_id=document_id,
        )

    def upsert_folder_index(
        self,
        *,
        folder: object,
        signals: tuple[object, ...] = (),
    ) -> None:
        return None

    def mark_folder_deleted(self, *, folder_id: str) -> DeletedFolderIdentity:
        return DeletedFolderIdentity(tenant="tenant-1", folder_id=folder_id)

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


class FakeDeadLetterProducer:
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


def make_application_storage(
    *,
    document_vectors: FakeDocumentVectorStore | None = None,
    signal_vectors: FakeSignalVectorStore | None = None,
    graph: FakeGraphStore | None = None,
) -> ApplicationStorage:
    document_vectors = document_vectors or FakeDocumentVectorStore()
    return ApplicationStorage(
        task_repository=FakeTaskRepository(),
        indexing_uow=FakeIndexingUnitOfWork(),
        indexed_document_sources=FakeIndexedDocumentSourceRepository(),
        chunk_vectors=document_vectors,
        document_vectors=document_vectors,
        signal_vectors=signal_vectors or FakeSignalVectorStore(),
        folder_vectors=FakeFolderVectorStore(),
        graph=graph or FakeGraphStore(),
    )


class BootstrapTests(unittest.TestCase):
    def test_api_settings_can_be_loaded_from_environment(self) -> None:
        keys = (
            "FOLDMIND_API_TITLE",
            "FOLDMIND_API_VERSION",
            "FOLDMIND_CORS_ORIGINS",
            "FOLDMIND_CORS_ALLOW_CREDENTIALS",
            "FOLDMIND_POSTGRES_DSN",
            "FOLDMIND_QDRANT_URL",
            "FOLDMIND_QDRANT_API_KEY",
            "FOLDMIND_NEO4J_URI",
            "FOLDMIND_NEO4J_USER",
            "FOLDMIND_NEO4J_PASSWORD",
            "FOLDMIND_AI_PROVIDER",
            "FOLDMIND_OPENAI_API_KEY",
            "FOLDMIND_OPENAI_BASE_URL",
            "FOLDMIND_LLM_MODEL",
            "FOLDMIND_EMBEDDING_MODEL",
            "FOLDMIND_EMBEDDING_VERSION",
            "FOLDMIND_CHUNKING_VERSION",
            "FOLDMIND_INDEX_SCHEMA_VERSION",
            "FOLDMIND_DOCUMENT_PROFILE_PROMPT_VERSION",
            "FOLDMIND_EMBEDDING_DIMENSIONS",
            "FOLDMIND_OPENAI_TIMEOUT_SECONDS",
            "FOLDMIND_OPENAI_MAX_RETRIES",
            "FOLDMIND_KAFKA_BOOTSTRAP_SERVERS",
            "FOLDMIND_KAFKA_OUTBOX_TOPIC",
            "FOLDMIND_OUTBOX_PROJECTION_TARGET",
            "FOLDMIND_KAFKA_DEAD_LETTER_TOPIC",
            "FOLDMIND_KAFKA_MAX_RETRIES",
            "FOLDMIND_KAFKA_RETRY_BACKOFF_SECONDS",
        )
        saved_environment = {key: os.environ.get(key) for key in keys}
        try:
            os.environ["FOLDMIND_API_TITLE"] = "Custom FoldMind"
            os.environ["FOLDMIND_API_VERSION"] = "9.9.9"
            os.environ["FOLDMIND_CORS_ORIGINS"] = "http://localhost:3000, https://app.test"
            os.environ["FOLDMIND_CORS_ALLOW_CREDENTIALS"] = "false"
            os.environ["FOLDMIND_POSTGRES_DSN"] = "postgresql://user:pass@postgres:5432/core"
            os.environ["FOLDMIND_QDRANT_URL"] = "http://qdrant:6333"
            os.environ["FOLDMIND_QDRANT_API_KEY"] = "qdrant-secret"
            os.environ["FOLDMIND_NEO4J_URI"] = "bolt://neo4j:7687"
            os.environ["FOLDMIND_NEO4J_USER"] = "neo4j"
            os.environ["FOLDMIND_NEO4J_PASSWORD"] = "neo4j-secret"
            os.environ["FOLDMIND_AI_PROVIDER"] = "openai"
            os.environ["FOLDMIND_OPENAI_API_KEY"] = "openai-secret"
            os.environ["FOLDMIND_OPENAI_BASE_URL"] = "https://api.openai.test/v1"
            os.environ["FOLDMIND_LLM_MODEL"] = "gpt-5-mini"
            os.environ["FOLDMIND_EMBEDDING_MODEL"] = "text-embedding-3-large"
            os.environ["FOLDMIND_EMBEDDING_VERSION"] = "embedding-prod-v1"
            os.environ["FOLDMIND_CHUNKING_VERSION"] = "chunking-prod-v1"
            os.environ["FOLDMIND_INDEX_SCHEMA_VERSION"] = "index-schema-prod-v1"
            os.environ["FOLDMIND_DOCUMENT_PROFILE_PROMPT_VERSION"] = "profile-prompt-prod-v1"
            os.environ["FOLDMIND_EMBEDDING_DIMENSIONS"] = "1024"
            os.environ["FOLDMIND_OPENAI_TIMEOUT_SECONDS"] = "45"
            os.environ["FOLDMIND_OPENAI_MAX_RETRIES"] = "4"
            os.environ["FOLDMIND_KAFKA_BOOTSTRAP_SERVERS"] = "kafka:9092"
            os.environ["FOLDMIND_KAFKA_OUTBOX_TOPIC"] = "indexing-events"
            os.environ["FOLDMIND_OUTBOX_PROJECTION_TARGET"] = "neo4j-graph"
            os.environ["FOLDMIND_KAFKA_DEAD_LETTER_TOPIC"] = "indexing-events.dlq"
            os.environ["FOLDMIND_KAFKA_MAX_RETRIES"] = "5"
            os.environ["FOLDMIND_KAFKA_RETRY_BACKOFF_SECONDS"] = "2.5"

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
            self.assertEqual(
                settings.document_profile_prompt_version,
                "profile-prompt-prod-v1",
            )
            self.assertEqual(settings.embedding_dimensions, 1024)
            self.assertEqual(settings.qdrant_collection_vector_size, 1024)
            self.assertEqual(settings.openai_timeout_seconds, 45)
            self.assertEqual(settings.openai_max_retries, 4)
            self.assertEqual(settings.kafka_bootstrap_servers, "kafka:9092")
            self.assertEqual(settings.kafka_outbox_topic, "indexing-events")
            self.assertEqual(
                settings.outbox_projection_target,
                OutboxProjectionTarget.NEO4J_GRAPH,
            )
            self.assertEqual(settings.kafka_dead_letter_topic, "indexing-events.dlq")
            self.assertEqual(settings.kafka_max_retries, 5)
            self.assertEqual(settings.kafka_retry_backoff_seconds, 2.5)
            self.assertIn("cors_origins", APISettings.model_fields)
            self.assertNotIn("cors_origins_csv", APISettings.model_fields)
            self.assertNotIn("kafka_consumer_group", APISettings.model_fields)
        finally:
            for key, value in saved_environment.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_api_settings_ignore_unprefixed_legacy_environment_names(self) -> None:
        legacy_keys = (
            "POSTGRES_DSN",
            "QDRANT_URL",
            "NEO4J_USER",
            "AI_PROVIDER",
            "OPENAI_API_KEY",
            "EMBEDDING_MODEL",
            "OUTBOX_PROJECTION_TARGET",
        )
        foldmind_keys = tuple(f"FOLDMIND_{key}" for key in legacy_keys)
        keys = legacy_keys + foldmind_keys
        saved_environment = {key: os.environ.get(key) for key in keys}
        try:
            for key in foldmind_keys:
                os.environ.pop(key, None)
            for key in legacy_keys:
                os.environ[key] = "legacy-value"

            settings = APISettings()

            self.assertIsNone(settings.postgres_dsn)
            self.assertIsNone(settings.qdrant_url)
            self.assertIsNone(settings.neo4j_user)
            self.assertEqual(settings.ai_provider, AIProvider.OPENAI)
            self.assertIsNone(settings.openai_api_key_value)
            self.assertIsNone(settings.embedding_model)
            self.assertIsNone(settings.outbox_projection_target)
        finally:
            for key, value in saved_environment.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_qdrant_vector_size_follows_embedding_dimensions(self) -> None:
        settings = APISettings(embedding_dimensions=1024)

        self.assertEqual(settings.qdrant_collection_vector_size, 1024)

        with self.assertRaisesRegex(
            ValueError,
            "FOLDMIND_QDRANT_VECTOR_SIZE must match FOLDMIND_EMBEDDING_DIMENSIONS",
        ):
            APISettings(embedding_dimensions=1024, qdrant_vector_size=1536)

    def test_settings_loads_environment_example_files(self) -> None:
        local = load_settings("examples/env/local.env")
        external = load_settings("examples/env/external.env")
        local_postgres_external_services = load_settings(
            "examples/env/local-postgres-external-services.env"
        )

        self.assertEqual(local.postgres_dsn, "postgresql://foldmind:foldmind@postgres:5432/foldmind_ai_core")
        self.assertEqual(local.qdrant_url, "http://qdrant:6333")
        self.assertEqual(local.neo4j_uri, "bolt://neo4j:7687")
        self.assertEqual(local.ai_provider, AIProvider.OPENAI)
        self.assertEqual(local.openai_api_key_value, "REPLACE_ME")
        self.assertIsNone(local.openai_base_url)
        self.assertIsNone(local.qdrant_api_key_value)
        self.assertEqual(local.llm_model, "gpt-4.1-mini")
        self.assertEqual(local.embedding_dimensions, 1536)
        self.assertEqual(local.document_profile_prompt_version, "document-profile-prompt-v1")
        self.assertEqual(local.kafka_bootstrap_servers, "kafka:9092")
        self.assertEqual(
            local.outbox_projection_target,
            OutboxProjectionTarget.NEO4J_GRAPH,
        )
        self.assertEqual(local.kafka_dead_letter_topic, "indexing-events.dlq")
        self.assertEqual(external.qdrant_api_key_value, "REPLACE_ME")
        self.assertEqual(external.kafka_outbox_topic, "indexing-events")
        self.assertEqual(
            external.outbox_projection_target,
            OutboxProjectionTarget.NEO4J_GRAPH,
        )
        self.assertEqual(
            local_postgres_external_services.qdrant_url,
            "https://REPLACE_ME.cloud.qdrant.io",
        )
        self.assertEqual(
            local_postgres_external_services.neo4j_uri,
            "bolt://host.docker.internal:7687",
        )
        self.assertEqual(
            local_postgres_external_services.kafka_bootstrap_servers,
            "host.docker.internal:9092",
        )
        self.assertEqual(
            local_postgres_external_services.outbox_projection_target,
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
                    local_postgres_external_services.outbox_consumer_group_for_projection(
                        target
                    ),
                    expected_group,
                )

    def test_settings_can_validate_storage_requirements(self) -> None:
        settings = APISettings(
            qdrant_url=None,
        )

        with self.assertRaisesRegex(ValueError, "FOLDMIND_QDRANT_URL is required"):
            settings.require_configured_storage()

    def test_standard_storage_requires_graph_database_credentials(self) -> None:
        settings = APISettings(
            qdrant_url="http://qdrant:6333",
            postgres_dsn="postgresql://user:pass@postgres:5432/core",
            neo4j_uri=None,
            neo4j_user=None,
            neo4j_password=None,
        )

        with self.assertRaisesRegex(ValueError, "FOLDMIND_NEO4J_URI"):
            settings.require_configured_storage()

    def test_required_settings_reject_blank_strings(self) -> None:
        settings = APISettings(
            openai_api_key=" ",
            embedding_model=" ",
            document_profile_prompt_version=" ",
            postgres_dsn=" ",
            qdrant_url=" ",
            neo4j_uri=" ",
            neo4j_user=" ",
            neo4j_password=" ",
            embedding_version=" ",
            chunking_version=" ",
            index_schema_version=" ",
            kafka_bootstrap_servers=" ",
        )

        for property_name in (
            "required_openai_api_key",
            "required_embedding_model",
            "required_document_profile_prompt_version",
            "required_postgres_dsn",
            "required_qdrant_url",
            "required_neo4j_uri",
            "required_neo4j_user",
            "required_neo4j_password",
            "required_embedding_version",
            "required_chunking_version",
            "required_index_schema_version",
            "required_kafka_bootstrap_servers",
        ):
            with self.subTest(property_name=property_name):
                with self.assertRaises(ValueError):
                    getattr(settings, property_name)

        with self.assertRaisesRegex(ValueError, "FOLDMIND_QDRANT_URL"):
            settings.require_configured_storage()

    def test_required_settings_return_stripped_values(self) -> None:
        settings = APISettings(
            embedding_model=" text-embedding-3-small ",
            postgres_dsn=" postgresql://user:pass@postgres:5432/core ",
            qdrant_url=" http://qdrant:6333 ",
        )

        self.assertEqual(settings.required_embedding_model, "text-embedding-3-small")
        self.assertEqual(
            settings.required_postgres_dsn,
            "postgresql://user:pass@postgres:5432/core",
        )
        self.assertEqual(settings.required_qdrant_url, "http://qdrant:6333")

    def test_bootstrap_wires_dependencies_into_app(self) -> None:
        document_vectors = FakeDocumentVectorStore()
        llm = FakeLLMProvider()
        graph = FakeGraphStore()
        dependencies = ApplicationDependencies(
            ai=AICapabilities(
                llm=llm,
                embeddings=FakeEmbeddingProvider(),
            ),
            storage=make_application_storage(
                document_vectors=document_vectors,
                graph=graph,
            ),
            prompt_store=FakePromptStore(),
        )

        settings = APISettings(
            allow_in_memory_workflow_checkpoint=True,
            embedding_model=TEST_EMBEDDING_MODEL,
            chunking_version=TEST_CHUNKING_VERSION,
            embedding_version=TEST_EMBEDDING_VERSION,
            index_schema_version=TEST_INDEX_SCHEMA_VERSION,
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
                    "created_at": "2026-05-01T10:00:00+09:00",
                    "updated_at": "2026-05-02T11:00:00+09:00",
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

        self.assertIsNotNone(use_cases.run_task)
        self.assertFalse(hasattr(use_cases, "answer_question"))
        self.assertFalse(hasattr(use_cases, "search_documents"))
        self.assertEqual(index_response.status_code, 200)
        outbox_events = dependencies.storage.indexing_uow.tx.events
        self.assertEqual(len(document_vectors.chunk_upserted), 0)
        self.assertEqual(len(graph.relationships), 0)
        self.assertEqual(len(graph.signals), 0)
        self.assertEqual(len(outbox_events), 1)
        self.assertEqual(outbox_events[0].event_type, "DOCUMENT_INDEXED")
        self.assertEqual(answer_response.status_code, 404)

    def test_outbox_worker_factory_wires_projection_use_cases_and_runtime(self) -> None:
        document_vectors = FakeDocumentVectorStore()
        graph = FakeGraphStore()
        storage = make_application_storage(
            document_vectors=document_vectors,
            graph=graph,
        )
        message = BrokerMessage(
            key=b"document:tenant-1:doc-1",
            topic="indexing-events",
            partition=0,
            offset=1,
            value=json.dumps(
                {
                    "event_id": "11111111-1111-4111-8111-111111111111",
                    "event_sequence": 1,
                    "tenant_id": "tenant-1",
                    "partition_key": "document:tenant-1:doc-1",
                    "source_kind": "document",
                    "source_id": "doc-1",
                    "event_type": "DOCUMENT_DELETED",
                    "payload_schema_version": 1,
                    "idempotency_key": "document-delete:tenant-1:doc-1",
                    "payload": {
                        "tenant": "tenant-1",
                        "document_id": "doc-1",
                    },
                }
            ).encode("utf-8"),
        )
        consumer = FakeBrokerConsumer([message])
        dead_letter = FakeDeadLetterProducer()
        settings = APISettings(
            allow_in_memory_workflow_checkpoint=True,
            kafka_bootstrap_servers="kafka:9092",
            outbox_projection_target=OutboxProjectionTarget.NEO4J_GRAPH,
            kafka_max_retries=0,
            embedding_model=TEST_EMBEDDING_MODEL,
            chunking_version=TEST_CHUNKING_VERSION,
            embedding_version=TEST_EMBEDDING_VERSION,
            index_schema_version=TEST_INDEX_SCHEMA_VERSION,
            document_profile_prompt_version=TEST_PROFILE_PROMPT_VERSION,
        )
        worker = build_outbox_worker(
            settings=settings,
            storage=storage,
            kafka_consumer=consumer,
            dead_letter_producer=dead_letter,
        )

        handled = worker.run_once()

        self.assertTrue(handled)
        self.assertEqual(consumer.committed, [message])
        self.assertEqual(document_vectors.deleted, [])
        self.assertEqual(graph.deleted_documents, ["doc-1"])
        self.assertEqual(dead_letter.published, [])

    def test_outbox_worker_factory_wires_one_projection_target_per_worker(self) -> None:
        document_vectors = FakeDocumentVectorStore()
        graph = FakeGraphStore()
        storage = make_application_storage(
            document_vectors=document_vectors,
            graph=graph,
        )
        message = BrokerMessage(
            key=b"document:tenant-1:doc-1",
            topic="indexing-events",
            partition=0,
            offset=1,
            value=json.dumps(
                {
                    "event_id": "11111111-1111-4111-8111-111111111111",
                    "event_sequence": 1,
                    "tenant_id": "tenant-1",
                    "partition_key": "document:tenant-1:doc-1",
                    "source_kind": "document",
                    "source_id": "doc-1",
                    "event_type": "DOCUMENT_DELETED",
                    "payload_schema_version": 1,
                    "idempotency_key": "document-delete:tenant-1:doc-1",
                    "payload": {
                        "tenant": "tenant-1",
                        "document_id": "doc-1",
                    },
                }
            ).encode("utf-8"),
        )
        consumer = FakeBrokerConsumer([message])
        dead_letter = FakeDeadLetterProducer()
        settings = APISettings(
            allow_in_memory_workflow_checkpoint=True,
            kafka_bootstrap_servers="kafka:9092",
            outbox_projection_target=OutboxProjectionTarget.QDRANT_DOCUMENT_CHUNKS,
            kafka_max_retries=0,
            embedding_model=TEST_EMBEDDING_MODEL,
            chunking_version=TEST_CHUNKING_VERSION,
            embedding_version=TEST_EMBEDDING_VERSION,
            index_schema_version=TEST_INDEX_SCHEMA_VERSION,
            document_profile_prompt_version=TEST_PROFILE_PROMPT_VERSION,
        )
        worker = build_outbox_worker(
            settings=settings,
            storage=storage,
            ai_capabilities=AICapabilities(
                llm=FakeLLMProvider(),
                embeddings=FakeEmbeddingProvider(),
            ),
            kafka_consumer=consumer,
            dead_letter_producer=dead_letter,
        )

        handled = worker.run_once()

        self.assertTrue(handled)
        self.assertEqual(consumer.committed, [message])
        self.assertEqual(document_vectors.deleted, ["doc-1"])
        self.assertEqual(graph.deleted_documents, [])
        self.assertEqual(dead_letter.published, [])

    def test_outbox_projection_storage_factory_builds_only_target_storage(self) -> None:
        settings = APISettings(
            postgres_dsn="postgresql://user:pass@postgres:5432/app",
            qdrant_url="http://qdrant:6333",
            neo4j_uri="bolt://neo4j:7687",
            neo4j_user="neo4j",
            neo4j_password="secret",
        )
        graph = FakeGraphStore()
        document_vectors = FakeDocumentVectorStore()
        folder_vectors = FakeFolderVectorStore()
        source_freshness = object()

        with (
            patch(
                "foldmind_ai_core.bootstrap.container.storage._build_neo4j_store",
                return_value=graph,
            ) as build_neo4j,
            patch(
                "foldmind_ai_core.bootstrap.container.storage."
                "_build_qdrant_document_chunk_vector_store",
                return_value=document_vectors,
            ) as build_chunk_vectors,
            patch(
                "foldmind_ai_core.bootstrap.container.storage."
                "_build_qdrant_document_vector_store",
                return_value=document_vectors,
            ) as build_document_vectors,
            patch(
                "foldmind_ai_core.bootstrap.container.storage."
                "_build_qdrant_folder_vector_store",
                return_value=folder_vectors,
            ) as build_folder_vectors,
            patch(
                "foldmind_ai_core.bootstrap.container.storage."
                "_build_source_freshness_checker",
                return_value=source_freshness,
            ),
        ):
            graph_storage = build_outbox_projection_storage(
                settings,
                target=OutboxProjectionTarget.NEO4J_GRAPH,
            )
            qdrant_stores = build_outbox_projection_storage(
                settings,
                target=OutboxProjectionTarget.QDRANT_DOCUMENTS,
            )

        self.assertIs(graph_storage.graph, graph)
        self.assertIs(graph_storage.source_freshness, source_freshness)
        self.assertIsNone(graph_storage.document_vectors)
        self.assertIs(qdrant_stores.document_vectors, document_vectors)
        self.assertIs(qdrant_stores.source_freshness, source_freshness)
        self.assertIsNone(qdrant_stores.chunk_vectors)
        self.assertIsNone(qdrant_stores.folder_vectors)
        self.assertIsNone(qdrant_stores.graph)
        self.assertEqual(build_neo4j.call_count, 1)
        self.assertEqual(build_chunk_vectors.call_count, 0)
        self.assertEqual(build_document_vectors.call_count, 1)
        self.assertEqual(build_folder_vectors.call_count, 0)

    def test_outbox_projection_factory_uses_vector_ledger_only_for_vector_targets(
        self,
    ) -> None:
        settings = APISettings(
            postgres_dsn="postgresql://user:pass@postgres:5432/app",
            qdrant_url="http://qdrant:6333",
            neo4j_uri="bolt://neo4j:7687",
            neo4j_user="neo4j",
            neo4j_password="secret",
            embedding_model=TEST_EMBEDDING_MODEL,
            embedding_version=TEST_EMBEDDING_VERSION,
        )
        graph = FakeGraphStore()
        document_vectors = FakeDocumentVectorStore()
        ledger = object()

        with (
            patch(
                "foldmind_ai_core.bootstrap.container.storage._build_neo4j_store",
                return_value=graph,
            ),
            patch(
                "foldmind_ai_core.bootstrap.container.storage."
                "_build_qdrant_document_vector_store",
                return_value=document_vectors,
            ),
            patch(
                "foldmind_ai_core.bootstrap.container.storage._build_projection_ledger",
                return_value=ledger,
            ) as build_projection_ledger,
        ):
            graph_storage = build_outbox_projection_storage(
                settings,
                target=OutboxProjectionTarget.NEO4J_GRAPH,
            )
            qdrant_storage = build_outbox_projection_storage(
                settings,
                target=OutboxProjectionTarget.QDRANT_DOCUMENTS,
            )

        self.assertIsNone(graph_storage.projection_ledger)
        self.assertIs(qdrant_storage.projection_ledger, ledger)
        build_projection_ledger.assert_called_once_with(settings)

    def test_configured_app_wires_storage_ai_and_packaged_prompts(self) -> None:
        document_vectors = FakeDocumentVectorStore()
        llm = FakeLLMProvider()
        storage = make_application_storage(document_vectors=document_vectors)
        ai_capabilities = AICapabilities(
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
            document_profile_prompt_version=TEST_PROFILE_PROMPT_VERSION,
        )

        app = build_configured_app(
            settings=settings,
            storage=storage,
            ai_capabilities=ai_capabilities,
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
        self.assertNotIn("/retrieval/search", paths)
        self.assertNotIn("/retrieval/answer", paths)
        self.assertIn("/indexing/documents", paths)
        self.assertIn("/tasks", paths)
        self.assertEqual(response.status_code, 404)

    def test_standard_storage_requires_task_repository_dsn(self) -> None:
        settings = APISettings(
            qdrant_url="http://qdrant:6333",
            postgres_dsn=None,
        )

        with self.assertRaisesRegex(ValueError, "FOLDMIND_POSTGRES_DSN is required"):
            settings.require_configured_storage()

    def test_openai_requires_api_key_and_rejects_unsupported_provider(self) -> None:
        with self.assertRaisesRegex(ValueError, "FOLDMIND_OPENAI_API_KEY is required"):
            build_ai_capabilities(APISettings(openai_api_key=None))

        settings = APISettings(
            openai_api_key="openai-secret",
            embedding_model=TEST_EMBEDDING_MODEL,
        )
        object.__setattr__(settings, "ai_provider", "unsupported")
        with self.assertRaisesRegex(RuntimeError, "Unsupported FOLDMIND_AI_PROVIDER"):
            build_ai_capabilities(settings)

    def test_default_prompt_store_uses_packaged_prompt_resources(self) -> None:
        repository = build_prompt_store(APISettings())

        self.assertIn("Answer Generation", repository.get(PROMPT_ANSWER_GENERATION))

    def test_workflow_artifact_registry_has_no_step_dependencies(self) -> None:
        registry = WorkflowArtifactRegistry()

        self.assertFalse(hasattr(registry, "find_documents"))
        self.assertFalse(hasattr(registry, "find_folders"))


if __name__ == "__main__":
    unittest.main()
