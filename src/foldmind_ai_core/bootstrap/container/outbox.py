from __future__ import annotations

from foldmind_ai_core.adapters.inbound.messaging.consumers.document_chunk_vector_consumer import (
    DocumentChunkVectorDeletedConsumer,
    DocumentChunkVectorIndexedConsumer,
)
from foldmind_ai_core.adapters.inbound.messaging.consumers.document_signal_vector_consumer import (
    DocumentSignalVectorsDeletedConsumer,
    DocumentSignalVectorsIndexedConsumer,
)
from foldmind_ai_core.adapters.inbound.messaging.consumers.document_vector_consumer import (
    DocumentVectorDeletedConsumer,
    DocumentVectorIndexedConsumer,
)
from foldmind_ai_core.adapters.inbound.messaging.consumers.folder_signal_vector_consumer import (
    FolderSignalVectorsDeletedConsumer,
    FolderSignalVectorsIndexedConsumer,
    FolderSignalVectorsInvalidatedConsumer,
)
from foldmind_ai_core.adapters.inbound.messaging.consumers.folder_vector_consumer import (
    FolderVectorDeletedConsumer,
    FolderVectorIndexedConsumer,
)
from foldmind_ai_core.adapters.inbound.messaging.consumers.graph_consumer import (
    DocumentGraphDeletedConsumer,
    DocumentGraphFolderRelationsIndexedConsumer,
    DocumentGraphIndexedConsumer,
    FolderGraphDeletedConsumer,
    FolderGraphIndexedConsumer,
    FolderSignalsGraphIndexedConsumer,
    FolderSignalsGraphInvalidatedConsumer,
)
from foldmind_ai_core.adapters.inbound.messaging.dispatcher import (
    OutboxEventDispatcher,
)
from foldmind_ai_core.bootstrap.container.dependencies import (
    AIProviders,
    OutboxProjectionStorage,
)
from foldmind_ai_core.bootstrap.settings import APISettings, OutboxProjectionTarget
from foldmind_ai_core.core.application.ports.outbound.session.projection_ledger_session import (
    ProjectionLedgerSessionProvider,
)
from foldmind_ai_core.core.application.models.vector_projection import VectorProjectionSpec
from foldmind_ai_core.core.application.services.projection.document_vector_projection_service import (  # noqa: E501
    DocumentVectorProjectionService,
)
from foldmind_ai_core.core.application.services.projection.folder_vector_projection_service import (
    FolderVectorProjectionService,
)
from foldmind_ai_core.core.application.services.projection.graph_projection_service import (
    GraphProjectionService,
)


def _build_outbox_dispatcher(
    *,
    ai: AIProviders | None,
    storage: OutboxProjectionStorage,
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
    ai: AIProviders | None,
    storage: OutboxProjectionStorage,
    target: OutboxProjectionTarget,
) -> OutboxEventDispatcher:
    ai = _required_outbox_ai_provider(ai, target=target)
    chunk_vectors = storage.chunk_vectors
    if chunk_vectors is None:
        raise RuntimeError("Document chunk vector store is required.")
    projection_ledger = _required_projection_ledger(storage)
    source_freshness = storage.source_freshness
    service = DocumentVectorProjectionService(
        embeddings=ai.embeddings,
        chunk_vectors=chunk_vectors,
        document_vectors=None,
        signal_vectors=None,
        projection_spec=None,
        projection_ledger=projection_ledger,
        source_freshness=source_freshness,
    )
    return OutboxEventDispatcher(
        document_indexed=DocumentChunkVectorIndexedConsumer(
            service=service,
        ),
        document_folder_relations_indexed=None,
        document_deleted=DocumentChunkVectorDeletedConsumer(
            service=service,
        ),
        folder_indexed=None,
        folder_deleted=None,
    )


def _build_document_vector_dispatcher(
    *,
    ai: AIProviders | None,
    storage: OutboxProjectionStorage,
    settings: APISettings,
    target: OutboxProjectionTarget,
) -> OutboxEventDispatcher:
    ai = _required_outbox_ai_provider(ai, target=target)
    document_vectors = storage.document_vectors
    if document_vectors is None:
        raise RuntimeError("Document vector store is required.")
    projection_spec = _vector_projection_spec(settings)
    projection_ledger = _required_projection_ledger(storage)
    source_freshness = storage.source_freshness
    service = DocumentVectorProjectionService(
        embeddings=ai.embeddings,
        chunk_vectors=None,
        document_vectors=document_vectors,
        signal_vectors=None,
        projection_spec=projection_spec,
        projection_ledger=projection_ledger,
        source_freshness=source_freshness,
    )
    return OutboxEventDispatcher(
        document_indexed=DocumentVectorIndexedConsumer(
            service=service,
        ),
        document_folder_relations_indexed=None,
        document_deleted=DocumentVectorDeletedConsumer(
            service=service,
        ),
        folder_indexed=None,
        folder_deleted=None,
    )


def _build_signal_vector_dispatcher(
    *,
    ai: AIProviders | None,
    storage: OutboxProjectionStorage,
    settings: APISettings,
    target: OutboxProjectionTarget,
) -> OutboxEventDispatcher:
    ai = _required_outbox_ai_provider(ai, target=target)
    signal_vectors = storage.signal_vectors
    if signal_vectors is None:
        raise RuntimeError("Signal vector store is required.")
    projection_spec = _vector_projection_spec(settings)
    projection_ledger = _required_projection_ledger(storage)
    source_freshness = storage.source_freshness
    document_service = DocumentVectorProjectionService(
        embeddings=ai.embeddings,
        chunk_vectors=None,
        document_vectors=None,
        signal_vectors=signal_vectors,
        projection_spec=projection_spec,
        projection_ledger=projection_ledger,
        source_freshness=source_freshness,
    )
    folder_service = FolderVectorProjectionService(
        embeddings=ai.embeddings,
        folder_vectors=None,
        signal_vectors=signal_vectors,
        projection_spec=projection_spec,
        projection_ledger=projection_ledger,
        source_freshness=source_freshness,
    )
    return OutboxEventDispatcher(
        document_indexed=DocumentSignalVectorsIndexedConsumer(
            service=document_service,
        ),
        document_folder_relations_indexed=None,
        document_deleted=DocumentSignalVectorsDeletedConsumer(
            service=document_service,
        ),
        folder_indexed=None,
        folder_signals_indexed=FolderSignalVectorsIndexedConsumer(
            service=folder_service,
        ),
        folder_signals_invalidated=FolderSignalVectorsInvalidatedConsumer(
            service=folder_service,
        ),
        folder_deleted=FolderSignalVectorsDeletedConsumer(
            service=folder_service,
        ),
    )


def _build_folder_vector_dispatcher(
    *,
    ai: AIProviders | None,
    storage: OutboxProjectionStorage,
    settings: APISettings,
    target: OutboxProjectionTarget,
) -> OutboxEventDispatcher:
    ai = _required_outbox_ai_provider(ai, target=target)
    folder_vectors = storage.folder_vectors
    if folder_vectors is None:
        raise RuntimeError("Folder vector store is required.")
    projection_spec = _vector_projection_spec(settings)
    projection_ledger = _required_projection_ledger(storage)
    source_freshness = storage.source_freshness
    service = FolderVectorProjectionService(
        embeddings=ai.embeddings,
        folder_vectors=folder_vectors,
        signal_vectors=None,
        projection_spec=projection_spec,
        projection_ledger=projection_ledger,
        source_freshness=source_freshness,
    )
    return OutboxEventDispatcher(
        document_indexed=None,
        document_folder_relations_indexed=None,
        document_deleted=None,
        folder_indexed=FolderVectorIndexedConsumer(
            service=service,
        ),
        folder_deleted=FolderVectorDeletedConsumer(
            service=service,
        ),
    )


def _build_graph_dispatcher(
    *,
    storage: OutboxProjectionStorage,
) -> OutboxEventDispatcher:
    graph = storage.graph
    if graph is None:
        raise RuntimeError("Graph store is required.")
    source_freshness = storage.source_freshness
    graph_projection = GraphProjectionService(
        graph=graph,
        source_freshness=source_freshness,
    )
    return OutboxEventDispatcher(
        document_indexed=DocumentGraphIndexedConsumer(
            service=graph_projection,
        ),
        document_folder_relations_indexed=DocumentGraphFolderRelationsIndexedConsumer(
            service=graph_projection,
        ),
        document_deleted=DocumentGraphDeletedConsumer(
            service=graph_projection,
        ),
        folder_indexed=FolderGraphIndexedConsumer(
            service=graph_projection,
        ),
        folder_signals_indexed=FolderSignalsGraphIndexedConsumer(
            service=graph_projection,
        ),
        folder_signals_invalidated=FolderSignalsGraphInvalidatedConsumer(
            service=graph_projection,
        ),
        folder_deleted=FolderGraphDeletedConsumer(
            service=graph_projection,
        ),
    )


def _required_outbox_ai_provider(
    ai: AIProviders | None,
    *,
    target: OutboxProjectionTarget,
) -> AIProviders:
    if ai is None:
        raise RuntimeError(f"AI providers are required for {target.value}.")
    return ai


def _required_projection_ledger(
    storage: OutboxProjectionStorage,
) -> ProjectionLedgerSessionProvider:
    if storage.projection_ledger is None:
        raise RuntimeError("Projection ledger session provider is required.")
    return storage.projection_ledger


def _vector_projection_spec(settings: APISettings) -> VectorProjectionSpec:
    return VectorProjectionSpec(
        embedding_model=settings.required_embedding_model,
        embedding_version=settings.required_embedding_version,
        index_schema_version=settings.required_index_schema_version,
    )
