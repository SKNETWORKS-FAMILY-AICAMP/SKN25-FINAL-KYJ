from __future__ import annotations

from foldmind_ai_core.adapters.inbound.messaging.broker import BrokerConsumer
from foldmind_ai_core.adapters.inbound.messaging.consumers.document_chunk_vector_consumer import (
    DocumentChunkVectorDeletedConsumer,
    DocumentChunkVectorIndexedConsumer,
)
from foldmind_ai_core.adapters.inbound.messaging.consumers.document_vector_consumer import (
    DocumentVectorDeletedConsumer,
    DocumentVectorIndexedConsumer,
)
from foldmind_ai_core.adapters.inbound.messaging.consumers.folder_vector_consumer import (
    FolderVectorDeletedConsumer,
    FolderVectorIndexedConsumer,
)
from foldmind_ai_core.adapters.inbound.messaging.consumers.folder_signal_vector_consumer import (
    FolderSignalVectorsDeletedConsumer,
    FolderSignalVectorsIndexedConsumer,
)
from foldmind_ai_core.adapters.inbound.messaging.consumers.graph_consumer import (
    DocumentGraphDeletedConsumer,
    DocumentGraphFolderRelationsIndexedConsumer,
    DocumentGraphIndexedConsumer,
    FolderGraphDeletedConsumer,
    FolderGraphIndexedConsumer,
)
from foldmind_ai_core.adapters.inbound.messaging.consumers.document_signal_vector_consumer import (
    DocumentSignalVectorsDeletedConsumer,
    DocumentSignalVectorsIndexedConsumer,
)
from foldmind_ai_core.adapters.inbound.messaging.dispatcher import (
    OutboxEventDispatcher,
)
from foldmind_ai_core.adapters.inbound.messaging.kafka import KafkaOutboxConsumer
from foldmind_ai_core.adapters.outbound.kafka.dead_letter_producer import (
    KafkaDeadLetterProducer,
)
from foldmind_ai_core.core.application.services.vector_projection_spec import VectorProjectionSpec
from foldmind_ai_core.core.application.use_cases.projection.document_chunk_vector_projection import (
    DeleteDocumentChunkVectorsUseCase,
    ProjectDocumentChunkVectorsUseCase,
)
from foldmind_ai_core.core.application.use_cases.projection.document_vector_projection import (
    DeleteDocumentSignalVectorsUseCase,
    DeleteDocumentVectorUseCase,
    ProjectDocumentSignalVectorsUseCase,
    ProjectDocumentVectorUseCase,
)
from foldmind_ai_core.core.application.use_cases.projection.folder_vector_projection import (
    DeleteFolderSignalVectorsUseCase,
    DeleteFolderVectorUseCase,
    ProjectFolderSignalVectorsUseCase,
    ProjectFolderVectorUseCase,
)
from foldmind_ai_core.core.application.use_cases.projection.graph_projection import (
    DeleteDocumentGraphUseCase,
    DeleteFolderGraphUseCase,
    ProjectDocumentFolderRelationsGraphUseCase,
    ProjectDocumentGraphUseCase,
    ProjectFolderGraphUseCase,
)
from foldmind_ai_core.bootstrap.container.dependencies import (
    AICapabilities,
    ProjectionStorage,
)
from foldmind_ai_core.bootstrap.container.providers import build_ai_capabilities
from foldmind_ai_core.bootstrap.container.storage import (
    build_outbox_projection_storage,
)
from foldmind_ai_core.bootstrap.settings import APISettings, OutboxProjectionTarget
from foldmind_ai_core.adapters.inbound.outbox_worker.runtime import (
    DeadLetterProducer,
    OutboxProjectionMessageConsumer,
    OutboxWorkerRuntime,
    RetryPolicy,
)


def build_outbox_dispatcher(
    *,
    ai: AICapabilities | None,
    storage: ProjectionStorage,
    settings: APISettings,
    target: OutboxProjectionTarget,
) -> OutboxEventDispatcher:
    match target:
        case OutboxProjectionTarget.QDRANT_DOCUMENT_CHUNKS:
            return _build_document_chunk_vector_dispatcher(
                ai=ai,
                storage=storage,
                target=target,
            )
        case OutboxProjectionTarget.QDRANT_DOCUMENTS:
            return _build_document_vector_dispatcher(
                ai=ai,
                storage=storage,
                settings=settings,
                target=target,
            )
        case OutboxProjectionTarget.QDRANT_SIGNALS:
            return _build_signal_vector_dispatcher(
                ai=ai,
                storage=storage,
                settings=settings,
                target=target,
            )
        case OutboxProjectionTarget.QDRANT_FOLDERS:
            return _build_folder_vector_dispatcher(
                ai=ai,
                storage=storage,
                settings=settings,
                target=target,
            )
        case OutboxProjectionTarget.NEO4J_GRAPH:
            return _build_graph_dispatcher(storage=storage)
    raise RuntimeError(f"Unsupported FOLDMIND_OUTBOX_PROJECTION_TARGET: {target}")


def _build_document_chunk_vector_dispatcher(
    *,
    ai: AICapabilities | None,
    storage: ProjectionStorage,
    target: OutboxProjectionTarget,
) -> OutboxEventDispatcher:
    ai = _required_outbox_ai_provider(ai, target=target)
    chunk_vectors = storage.chunk_vectors
    if chunk_vectors is None:
        raise RuntimeError("Document chunk vector store is required.")
    projection_ledger = getattr(storage, "projection_ledger", None)
    source_freshness = getattr(storage, "source_freshness", None)
    return OutboxEventDispatcher(
        document_indexed=DocumentChunkVectorIndexedConsumer(
            use_case=ProjectDocumentChunkVectorsUseCase(
                embeddings=ai.embeddings,
                chunk_vectors=chunk_vectors,
                projection_ledger=projection_ledger,
                source_freshness=source_freshness,
            ),
        ),
        document_folder_relations_indexed=None,
        document_deleted=DocumentChunkVectorDeletedConsumer(
            use_case=DeleteDocumentChunkVectorsUseCase(
                chunk_vectors=chunk_vectors,
                projection_ledger=projection_ledger,
            ),
        ),
        folder_indexed=None,
        folder_deleted=None,
    )


def _build_document_vector_dispatcher(
    *,
    ai: AICapabilities | None,
    storage: ProjectionStorage,
    settings: APISettings,
    target: OutboxProjectionTarget,
) -> OutboxEventDispatcher:
    ai = _required_outbox_ai_provider(ai, target=target)
    document_vectors = storage.document_vectors
    if document_vectors is None:
        raise RuntimeError("Document vector store is required.")
    projection_spec = _vector_projection_spec(settings)
    projection_ledger = getattr(storage, "projection_ledger", None)
    source_freshness = getattr(storage, "source_freshness", None)
    return OutboxEventDispatcher(
        document_indexed=DocumentVectorIndexedConsumer(
            use_case=ProjectDocumentVectorUseCase(
                embeddings=ai.embeddings,
                document_vectors=document_vectors,
                projection_spec=projection_spec,
                projection_ledger=projection_ledger,
                source_freshness=source_freshness,
            ),
        ),
        document_folder_relations_indexed=None,
        document_deleted=DocumentVectorDeletedConsumer(
            use_case=DeleteDocumentVectorUseCase(
                document_vectors=document_vectors,
                projection_ledger=projection_ledger,
            ),
        ),
        folder_indexed=None,
        folder_deleted=None,
    )


def _build_signal_vector_dispatcher(
    *,
    ai: AICapabilities | None,
    storage: ProjectionStorage,
    settings: APISettings,
    target: OutboxProjectionTarget,
) -> OutboxEventDispatcher:
    ai = _required_outbox_ai_provider(ai, target=target)
    signal_vectors = storage.signal_vectors
    if signal_vectors is None:
        raise RuntimeError("Signal vector store is required.")
    projection_spec = _vector_projection_spec(settings)
    projection_ledger = getattr(storage, "projection_ledger", None)
    source_freshness = getattr(storage, "source_freshness", None)
    return OutboxEventDispatcher(
        document_indexed=DocumentSignalVectorsIndexedConsumer(
            use_case=ProjectDocumentSignalVectorsUseCase(
                embeddings=ai.embeddings,
                signal_vectors=signal_vectors,
                projection_spec=projection_spec,
                projection_ledger=projection_ledger,
                source_freshness=source_freshness,
            ),
        ),
        document_folder_relations_indexed=None,
        document_deleted=DocumentSignalVectorsDeletedConsumer(
            use_case=DeleteDocumentSignalVectorsUseCase(
                signal_vectors=signal_vectors,
                projection_ledger=projection_ledger,
            ),
        ),
        folder_indexed=FolderSignalVectorsIndexedConsumer(
            use_case=ProjectFolderSignalVectorsUseCase(
                embeddings=ai.embeddings,
                signal_vectors=signal_vectors,
                projection_spec=projection_spec,
                projection_ledger=projection_ledger,
                source_freshness=source_freshness,
            ),
        ),
        folder_deleted=FolderSignalVectorsDeletedConsumer(
            use_case=DeleteFolderSignalVectorsUseCase(
                signal_vectors=signal_vectors,
                projection_ledger=projection_ledger,
            ),
        ),
    )


def _build_folder_vector_dispatcher(
    *,
    ai: AICapabilities | None,
    storage: ProjectionStorage,
    settings: APISettings,
    target: OutboxProjectionTarget,
) -> OutboxEventDispatcher:
    ai = _required_outbox_ai_provider(ai, target=target)
    folder_vectors = storage.folder_vectors
    if folder_vectors is None:
        raise RuntimeError("Folder vector store is required.")
    projection_spec = _vector_projection_spec(settings)
    projection_ledger = getattr(storage, "projection_ledger", None)
    source_freshness = getattr(storage, "source_freshness", None)
    return OutboxEventDispatcher(
        document_indexed=None,
        document_folder_relations_indexed=None,
        document_deleted=None,
        folder_indexed=FolderVectorIndexedConsumer(
            use_case=ProjectFolderVectorUseCase(
                embeddings=ai.embeddings,
                folder_vectors=folder_vectors,
                projection_spec=projection_spec,
                projection_ledger=projection_ledger,
                source_freshness=source_freshness,
            ),
        ),
        folder_deleted=FolderVectorDeletedConsumer(
            use_case=DeleteFolderVectorUseCase(
                folder_vectors=folder_vectors,
                projection_ledger=projection_ledger,
            ),
        ),
    )


def _build_graph_dispatcher(
    *,
    storage: ProjectionStorage,
) -> OutboxEventDispatcher:
    graph = storage.graph
    if graph is None:
        raise RuntimeError("Graph store is required.")
    source_freshness = getattr(storage, "source_freshness", None)
    return OutboxEventDispatcher(
        document_indexed=DocumentGraphIndexedConsumer(
            use_case=ProjectDocumentGraphUseCase(
                graph=graph,
                source_freshness=source_freshness,
            ),
        ),
        document_folder_relations_indexed=DocumentGraphFolderRelationsIndexedConsumer(
            use_case=ProjectDocumentFolderRelationsGraphUseCase(
                graph=graph,
                source_freshness=source_freshness,
            ),
        ),
        document_deleted=DocumentGraphDeletedConsumer(
            use_case=DeleteDocumentGraphUseCase(
                graph=graph,
            ),
        ),
        folder_indexed=FolderGraphIndexedConsumer(
            use_case=ProjectFolderGraphUseCase(
                graph=graph,
                source_freshness=source_freshness,
            ),
        ),
        folder_deleted=FolderGraphDeletedConsumer(
            use_case=DeleteFolderGraphUseCase(
                graph=graph,
            ),
        ),
    )


def _required_outbox_ai_provider(
    ai: AICapabilities | None,
    *,
    target: OutboxProjectionTarget,
) -> AICapabilities:
    if ai is None:
        raise RuntimeError(f"AI capabilities are required for {target.value}.")
    return ai


def _vector_projection_spec(settings: APISettings) -> VectorProjectionSpec:
    return VectorProjectionSpec(
        embedding_model=settings.required_embedding_model,
        embedding_version=settings.required_embedding_version,
        index_schema_version=settings.required_index_schema_version,
    )


def build_outbox_worker(
    *,
    settings: APISettings | None = None,
    storage: ProjectionStorage | None = None,
    ai_capabilities: AICapabilities | None = None,
    kafka_consumer: BrokerConsumer | None = None,
    dead_letter_producer: DeadLetterProducer | None = None,
) -> OutboxWorkerRuntime:
    settings = settings or APISettings()
    target = settings.required_outbox_projection_target
    ai = ai_capabilities
    if ai is None and target in {
        OutboxProjectionTarget.QDRANT_DOCUMENT_CHUNKS,
        OutboxProjectionTarget.QDRANT_DOCUMENTS,
        OutboxProjectionTarget.QDRANT_SIGNALS,
        OutboxProjectionTarget.QDRANT_FOLDERS,
    }:
        ai = build_ai_capabilities(settings)
    storage = storage or build_outbox_projection_storage(
        settings,
        target=target,
    )
    consumer = kafka_consumer or KafkaOutboxConsumer(
        bootstrap_servers=settings.required_kafka_bootstrap_servers,
        topic=settings.kafka_outbox_topic,
        group_id=settings.outbox_consumer_group_for_projection(target),
    )
    producer = dead_letter_producer or KafkaDeadLetterProducer(
        bootstrap_servers=settings.required_kafka_bootstrap_servers,
    )
    return OutboxWorkerRuntime(
        consumer=consumer,
        message_consumer=OutboxProjectionMessageConsumer(
            dispatcher=build_outbox_dispatcher(
                ai=ai,
                storage=storage,
                settings=settings,
                target=target,
            ),
            dead_letter_producer=producer,
            dead_letter_topic=settings.kafka_dead_letter_topic,
            projection_target=target.value,
            retry_policy=RetryPolicy(
                max_retries=settings.kafka_max_retries,
                backoff_seconds=settings.kafka_retry_backoff_seconds,
            ),
        ),
    )
