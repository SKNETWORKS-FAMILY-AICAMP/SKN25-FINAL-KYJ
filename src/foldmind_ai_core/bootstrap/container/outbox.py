from __future__ import annotations

from foldmind_ai_core.adapters.inbound.messaging.broker import BrokerConsumer
from foldmind_ai_core.adapters.inbound.messaging.consumer import (
    DocumentChunkVectorDeletedConsumer,
    DocumentChunkVectorIndexedConsumer,
    DocumentGraphDeletedConsumer,
    DocumentGraphIndexedConsumer,
    DocumentVectorDeletedConsumer,
    DocumentVectorIndexedConsumer,
    FolderGraphDeletedConsumer,
    FolderGraphIndexedConsumer,
    FolderVectorDeletedConsumer,
    FolderVectorIndexedConsumer,
)
from foldmind_ai_core.adapters.inbound.messaging.dispatcher import (
    IgnoreOutboxEventConsumer,
    OutboxEventDispatcher,
)
from foldmind_ai_core.adapters.inbound.messaging.kafka import KafkaOutboxConsumer
from foldmind_ai_core.adapters.outbound.kafka.dlq_producer import KafkaDlqProducer
from foldmind_ai_core.application.ports.outbound.graph_repository import GraphRepository
from foldmind_ai_core.application.ports.outbound.vector_repository import (
    DocumentChunkVectorRepository,
    DocumentVectorRepository,
    FolderVectorRepository,
)
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
from foldmind_ai_core.bootstrap.container.dependencies import (
    AIProviderAdapters,
    OutboxProjectionRepositories,
)
from foldmind_ai_core.bootstrap.container.providers import build_ai_provider
from foldmind_ai_core.bootstrap.container.repositories import (
    build_outbox_projection_repository_adapter,
)
from foldmind_ai_core.bootstrap.settings import APISettings, OutboxProjectionTarget
from foldmind_ai_core.workers.outbox_runtime import (
    DlqProducer,
    OutboxFreshnessStore,
    OutboxMessageProcessor,
    OutboxWorkerRuntime,
    RetryPolicy,
)


def build_outbox_dispatcher(
    *,
    ai: AIProviderAdapters | None,
    repositories: OutboxProjectionRepositories,
    settings: APISettings,
    target: OutboxProjectionTarget,
) -> OutboxEventDispatcher:
    match target:
        case OutboxProjectionTarget.QDRANT_DOCUMENT_CHUNKS:
            return _build_document_chunk_vector_dispatcher(
                ai=ai,
                repositories=repositories,
                target=target,
            )
        case OutboxProjectionTarget.QDRANT_DOCUMENTS:
            return _build_document_vector_dispatcher(
                ai=ai,
                repositories=repositories,
                settings=settings,
                target=target,
            )
        case OutboxProjectionTarget.QDRANT_FOLDERS:
            return _build_folder_vector_dispatcher(
                ai=ai,
                repositories=repositories,
                settings=settings,
                target=target,
            )
        case OutboxProjectionTarget.NEO4J_GRAPH:
            return _build_graph_dispatcher(repositories=repositories)
    raise RuntimeError(f"Unsupported OUTBOX_PROJECTION_TARGET: {target}")


def _build_document_chunk_vector_dispatcher(
    *,
    ai: AIProviderAdapters | None,
    repositories: OutboxProjectionRepositories,
    target: OutboxProjectionTarget,
) -> OutboxEventDispatcher:
    ai = _required_outbox_ai_provider(ai, target=target)
    chunk_vectors = _required_chunk_vectors(repositories)
    ignored = IgnoreOutboxEventConsumer()
    return OutboxEventDispatcher(
        document_indexed=DocumentChunkVectorIndexedConsumer(
            use_case=HandleDocumentChunkVectorIndexedProjectionUseCase(
                embeddings=ai.embeddings,
                chunk_vectors=chunk_vectors,
            ),
        ),
        document_deleted=DocumentChunkVectorDeletedConsumer(
            use_case=HandleDocumentChunkVectorDeletedProjectionUseCase(
                chunk_vectors=chunk_vectors,
            ),
        ),
        folder_indexed=ignored,
        folder_deleted=ignored,
    )


def _build_document_vector_dispatcher(
    *,
    ai: AIProviderAdapters | None,
    repositories: OutboxProjectionRepositories,
    settings: APISettings,
    target: OutboxProjectionTarget,
) -> OutboxEventDispatcher:
    ai = _required_outbox_ai_provider(ai, target=target)
    document_vectors = _required_document_vectors(repositories)
    projection_spec = _vector_projection_spec(settings)
    ignored = IgnoreOutboxEventConsumer()
    return OutboxEventDispatcher(
        document_indexed=DocumentVectorIndexedConsumer(
            use_case=HandleDocumentVectorIndexedProjectionUseCase(
                embeddings=ai.embeddings,
                document_vectors=document_vectors,
                projection_spec=projection_spec,
            ),
        ),
        document_deleted=DocumentVectorDeletedConsumer(
            use_case=HandleDocumentVectorDeletedProjectionUseCase(
                document_vectors=document_vectors,
            ),
        ),
        folder_indexed=ignored,
        folder_deleted=ignored,
    )


def _build_folder_vector_dispatcher(
    *,
    ai: AIProviderAdapters | None,
    repositories: OutboxProjectionRepositories,
    settings: APISettings,
    target: OutboxProjectionTarget,
) -> OutboxEventDispatcher:
    ai = _required_outbox_ai_provider(ai, target=target)
    folder_vectors = _required_folder_vectors(repositories)
    projection_spec = _vector_projection_spec(settings)
    ignored = IgnoreOutboxEventConsumer()
    return OutboxEventDispatcher(
        document_indexed=ignored,
        document_deleted=ignored,
        folder_indexed=FolderVectorIndexedConsumer(
            use_case=HandleFolderVectorIndexedProjectionUseCase(
                embeddings=ai.embeddings,
                folder_vectors=folder_vectors,
                projection_spec=projection_spec,
            ),
        ),
        folder_deleted=FolderVectorDeletedConsumer(
            use_case=HandleFolderVectorDeletedProjectionUseCase(
                folder_vectors=folder_vectors,
            ),
        ),
    )


def _build_graph_dispatcher(
    *,
    repositories: OutboxProjectionRepositories,
) -> OutboxEventDispatcher:
    graph = _required_graph(repositories)
    return OutboxEventDispatcher(
        document_indexed=DocumentGraphIndexedConsumer(
            use_case=HandleDocumentGraphIndexedProjectionUseCase(graph=graph),
        ),
        document_deleted=DocumentGraphDeletedConsumer(
            use_case=HandleDocumentGraphDeletedProjectionUseCase(graph=graph),
        ),
        folder_indexed=FolderGraphIndexedConsumer(
            use_case=HandleFolderGraphIndexedProjectionUseCase(graph=graph),
        ),
        folder_deleted=FolderGraphDeletedConsumer(
            use_case=HandleFolderGraphDeletedProjectionUseCase(graph=graph),
        ),
    )


def _required_outbox_ai_provider(
    ai: AIProviderAdapters | None,
    *,
    target: OutboxProjectionTarget,
) -> AIProviderAdapters:
    if ai is None:
        raise RuntimeError(f"AI provider adapters are required for {target.value}.")
    return ai


def _vector_projection_spec(settings: APISettings) -> VectorProjectionSpec:
    return VectorProjectionSpec(
        embedding_model=settings.required_embedding_model,
        embedding_version=settings.required_embedding_version,
        index_schema_version=settings.required_index_schema_version,
    )


def _outbox_target_requires_ai(target: OutboxProjectionTarget) -> bool:
    return target in {
        OutboxProjectionTarget.QDRANT_DOCUMENT_CHUNKS,
        OutboxProjectionTarget.QDRANT_DOCUMENTS,
        OutboxProjectionTarget.QDRANT_FOLDERS,
    }


def _required_chunk_vectors(
    repositories: OutboxProjectionRepositories,
) -> DocumentChunkVectorRepository:
    if repositories.chunk_vectors is None:
        raise RuntimeError("Document chunk vector repository is required.")
    return repositories.chunk_vectors


def _required_document_vectors(
    repositories: OutboxProjectionRepositories,
) -> DocumentVectorRepository:
    if repositories.document_vectors is None:
        raise RuntimeError("Document vector repository is required.")
    return repositories.document_vectors


def _required_folder_vectors(
    repositories: OutboxProjectionRepositories,
) -> FolderVectorRepository:
    if repositories.folder_vectors is None:
        raise RuntimeError("Folder vector repository is required.")
    return repositories.folder_vectors


def _required_graph(repositories: OutboxProjectionRepositories) -> GraphRepository:
    if repositories.graph is None:
        raise RuntimeError("Graph repository is required.")
    return repositories.graph


def build_outbox_worker(
    *,
    settings: APISettings | None = None,
    repository_adapter: OutboxProjectionRepositories | None = None,
    ai_provider_adapters: AIProviderAdapters | None = None,
    kafka_consumer: BrokerConsumer | None = None,
    dlq_producer: DlqProducer | None = None,
    outbox_freshness_store: OutboxFreshnessStore | None = None,
) -> OutboxWorkerRuntime:
    settings = settings or APISettings()
    target = settings.required_outbox_projection_target
    ai = ai_provider_adapters
    if ai is None and _outbox_target_requires_ai(target):
        ai = build_ai_provider(settings)
    repositories = repository_adapter or build_outbox_projection_repository_adapter(
        settings,
        target=target,
    )
    consumer = kafka_consumer or KafkaOutboxConsumer(
        bootstrap_servers=settings.required_kafka_bootstrap_servers,
        topic=settings.kafka_outbox_topic,
        group_id=settings.outbox_consumer_group_for_projection(target),
    )
    producer = dlq_producer or KafkaDlqProducer(
        bootstrap_servers=settings.required_kafka_bootstrap_servers,
    )
    freshness_store = outbox_freshness_store or _build_outbox_freshness_store(settings)
    return OutboxWorkerRuntime(
        consumer=consumer,
        processor=OutboxMessageProcessor(
            dispatcher=build_outbox_dispatcher(
                ai=ai,
                repositories=repositories,
                settings=settings,
                target=target,
            ),
            freshness_store=freshness_store,
            dlq_producer=producer,
            dlq_topic=settings.kafka_dlq_topic,
            projection_target=target.value,
            retry_policy=RetryPolicy(
                max_retries=settings.kafka_max_retries,
                backoff_seconds=settings.kafka_retry_backoff_seconds,
            ),
        ),
    )


def _build_outbox_freshness_store(settings: APISettings) -> OutboxFreshnessStore:
    from foldmind_ai_core.adapters.outbound.postgres.client import PostgresClient
    from foldmind_ai_core.adapters.outbound.postgres.outbox_repository import (
        PostgresOutboxRepository,
    )
    from foldmind_ai_core.adapters.outbound.postgres.settings import PostgresSettings

    return PostgresOutboxRepository(
        client=PostgresClient(
            settings=PostgresSettings(dsn=settings.required_postgres_dsn),
        )
    )
