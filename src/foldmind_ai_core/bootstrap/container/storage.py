from __future__ import annotations

from typing import Any

from foldmind_ai_core.bootstrap.container.dependencies import (
    ApplicationStorage,
    OutboxProjectionStorage,
)
from foldmind_ai_core.bootstrap.settings import APISettings, OutboxProjectionTarget
from foldmind_ai_core.core.application.ports.outbound.graph_store import GraphStore
from foldmind_ai_core.core.application.ports.outbound.indexed_document_source import (
    IndexedDocumentSourceRepository,
)
from foldmind_ai_core.core.application.ports.outbound.indexing_unit_of_work import (
    IndexingUnitOfWork,
)
from foldmind_ai_core.core.application.ports.outbound.keyword_search import (
    DocumentKeywordSearchStore,
)
from foldmind_ai_core.core.application.ports.outbound.task_repository import TaskRepository
from foldmind_ai_core.core.application.ports.outbound.vector_store import (
    DocumentChunkVectorStore,
    DocumentVectorStore,
    FolderVectorStore,
    SignalVectorStore,
)


def build_application_storage(settings: APISettings) -> ApplicationStorage:
    settings.require_configured_storage()

    (
        task_repository,
        indexing_uow,
        indexed_document_sources,
        keyword_chunks,
    ) = _build_postgres_storage(settings)
    (
        chunk_vectors,
        document_vectors,
        signal_vectors,
        folder_vectors,
    ) = _build_qdrant_stores(settings)
    graph = _build_neo4j_store(settings)

    return ApplicationStorage(
        task_repository=task_repository,
        indexing_uow=indexing_uow,
        indexed_document_sources=indexed_document_sources,
        keyword_chunks=keyword_chunks,
        chunk_vectors=chunk_vectors,
        document_vectors=document_vectors,
        signal_vectors=signal_vectors,
        folder_vectors=folder_vectors,
        graph=graph,
    )


def build_outbox_projection_storage(
    settings: APISettings,
    *,
    target: OutboxProjectionTarget,
) -> OutboxProjectionStorage:
    projection_ledger = (
        _build_projection_ledger(settings)
        if settings.postgres_dsn and target is not OutboxProjectionTarget.NEO4J_GRAPH
        else None
    )
    source_freshness = _build_source_freshness_checker(settings)
    if target is OutboxProjectionTarget.QDRANT_DOCUMENT_CHUNKS:
        return OutboxProjectionStorage(
            chunk_vectors=_build_qdrant_document_chunk_vector_store(settings),
            projection_ledger=projection_ledger,
            source_freshness=source_freshness,
        )
    if target is OutboxProjectionTarget.QDRANT_DOCUMENTS:
        return OutboxProjectionStorage(
            document_vectors=_build_qdrant_document_vector_store(settings),
            projection_ledger=projection_ledger,
            source_freshness=source_freshness,
        )
    if target is OutboxProjectionTarget.QDRANT_SIGNALS:
        return OutboxProjectionStorage(
            signal_vectors=_build_qdrant_signal_vector_store(settings),
            projection_ledger=projection_ledger,
            source_freshness=source_freshness,
        )
    if target is OutboxProjectionTarget.QDRANT_FOLDERS:
        return OutboxProjectionStorage(
            folder_vectors=_build_qdrant_folder_vector_store(settings),
            projection_ledger=projection_ledger,
            source_freshness=source_freshness,
        )
    if target is OutboxProjectionTarget.NEO4J_GRAPH:
        return OutboxProjectionStorage(
            graph=_build_neo4j_store(settings),
            source_freshness=source_freshness,
        )
    raise RuntimeError(f"Unsupported FOLDMIND_OUTBOX_PROJECTION_TARGET: {target}")


def _build_postgres_storage(
    settings: APISettings,
) -> tuple[
    TaskRepository,
    IndexingUnitOfWork,
    IndexedDocumentSourceRepository,
    DocumentKeywordSearchStore,
]:
    from foldmind_ai_core.adapters.outbound.postgres.client import PostgresClient
    from foldmind_ai_core.adapters.outbound.postgres.index_repository import (
        PostgresIndexRepository,
    )
    from foldmind_ai_core.adapters.outbound.postgres.document_keyword_search_store import (
        PostgresDocumentKeywordSearchStore,
    )
    from foldmind_ai_core.adapters.outbound.postgres.indexed_document_source_repository import (
        PostgresIndexedDocumentSourceRepository,
    )
    from foldmind_ai_core.adapters.outbound.postgres.indexing_unit_of_work import (
        PostgresIndexingUnitOfWork,
    )
    from foldmind_ai_core.adapters.outbound.postgres.outbox_repository import (
        PostgresOutboxRepository,
    )
    from foldmind_ai_core.adapters.outbound.postgres.settings import PostgresSettings
    from foldmind_ai_core.adapters.outbound.postgres.task_repository import (
        PostgresTaskRepository,
    )

    postgres_dsn = settings.required_postgres_dsn
    postgres_client = PostgresClient(settings=PostgresSettings(dsn=postgres_dsn))
    index_repository = PostgresIndexRepository()
    outbox_repository = PostgresOutboxRepository(client=postgres_client)
    return (
        PostgresTaskRepository(client=postgres_client),
        PostgresIndexingUnitOfWork(
            client=postgres_client,
            index_repository=index_repository,
            outbox_repository=outbox_repository,
        ),
        PostgresIndexedDocumentSourceRepository(client=postgres_client),
        PostgresDocumentKeywordSearchStore(client=postgres_client),
    )


def _build_qdrant_stores(
    settings: APISettings,
) -> tuple[
    DocumentChunkVectorStore,
    DocumentVectorStore,
    SignalVectorStore,
    FolderVectorStore,
]:
    qdrant_settings = _build_qdrant_settings(settings)
    return (
        _build_qdrant_document_chunk_vector_store(
            settings,
            qdrant_settings=qdrant_settings,
        ),
        _build_qdrant_document_vector_store(
            settings,
            qdrant_settings=qdrant_settings,
        ),
        _build_qdrant_signal_vector_store(
            settings,
            qdrant_settings=qdrant_settings,
        ),
        _build_qdrant_folder_vector_store(
            settings,
            qdrant_settings=qdrant_settings,
        ),
    )


def _build_qdrant_document_chunk_vector_store(
    settings: APISettings,
    *,
    qdrant_settings: Any | None = None,
) -> DocumentChunkVectorStore:
    from foldmind_ai_core.adapters.outbound.qdrant.client import (
        QdrantCollectionConfig,
    )
    from foldmind_ai_core.adapters.outbound.qdrant.stores.document_chunk_vector_store import (
        QdrantDocumentChunkVectorStore,
    )

    qdrant_settings = qdrant_settings or _build_qdrant_settings(settings)
    return QdrantDocumentChunkVectorStore(
        client=_qdrant_collection_client(
            settings=qdrant_settings,
            config=QdrantCollectionConfig(
                collection_name=settings.qdrant_document_chunk_collection,
                vector_size=settings.qdrant_collection_vector_size,
                distance=settings.qdrant_distance,
                payload_indexes=(
                    "tenant",
                    "document_id",
                    "document_type",
                    "chunk_id",
                    "source_version",
                    "content_digest",
                    "source_input_digest",
                    "vector_input_digest",
                    "created_at",
                    "updated_at",
                ),
            ),
        )
    )


def _build_qdrant_document_vector_store(
    settings: APISettings,
    *,
    qdrant_settings: Any | None = None,
) -> DocumentVectorStore:
    from foldmind_ai_core.adapters.outbound.qdrant.client import (
        QdrantCollectionConfig,
    )
    from foldmind_ai_core.adapters.outbound.qdrant.stores.document_vector_store import (
        QdrantDocumentVectorStore,
    )

    qdrant_settings = qdrant_settings or _build_qdrant_settings(settings)
    return QdrantDocumentVectorStore(
        client=_qdrant_collection_client(
            settings=qdrant_settings,
            config=QdrantCollectionConfig(
                collection_name=settings.qdrant_document_collection,
                vector_size=settings.qdrant_collection_vector_size,
                distance=settings.qdrant_distance,
                payload_indexes=(
                    "tenant",
                    "document_id",
                    "document_type",
                    "source_version",
                    "content_digest",
                    "source_input_digest",
                    "vector_input_digest",
                    "created_at",
                    "updated_at",
                ),
            ),
        )
    )


def _build_qdrant_signal_vector_store(
    settings: APISettings,
    *,
    qdrant_settings: Any | None = None,
) -> SignalVectorStore:
    from foldmind_ai_core.adapters.outbound.qdrant.client import (
        QdrantCollectionConfig,
    )
    from foldmind_ai_core.adapters.outbound.qdrant.stores.signal_vector_store import (
        QdrantSignalVectorStore,
    )

    qdrant_settings = qdrant_settings or _build_qdrant_settings(settings)
    return QdrantSignalVectorStore(
        client=_qdrant_collection_client(
            settings=qdrant_settings,
            config=QdrantCollectionConfig(
                collection_name=settings.qdrant_signal_collection,
                vector_size=settings.qdrant_collection_vector_size,
                distance=settings.qdrant_distance,
                payload_indexes=(
                    "tenant",
                    "owner_kind",
                    "document_id",
                    "document_type",
                    "folder_id",
                    "signal_type",
                    "signal_key",
                    "source_version",
                    "content_digest",
                    "source_input_digest",
                    "vector_input_digest",
                    "signal_generation_version",
                ),
            ),
        )
    )


def _build_qdrant_folder_vector_store(
    settings: APISettings,
    *,
    qdrant_settings: Any | None = None,
) -> FolderVectorStore:
    from foldmind_ai_core.adapters.outbound.qdrant.client import (
        QdrantCollectionConfig,
    )
    from foldmind_ai_core.adapters.outbound.qdrant.stores.folder_vector_store import (
        QdrantFolderVectorStore,
    )

    qdrant_settings = qdrant_settings or _build_qdrant_settings(settings)
    return QdrantFolderVectorStore(
        client=_qdrant_collection_client(
            settings=qdrant_settings,
            config=QdrantCollectionConfig(
                collection_name=settings.qdrant_folder_collection,
                vector_size=settings.qdrant_collection_vector_size,
                distance=settings.qdrant_distance,
                payload_indexes=(
                    "tenant",
                    "folder_id",
                    "source_version",
                    "source_input_digest",
                    "vector_input_digest",
                    "created_at",
                    "updated_at",
                ),
            ),
        )
    )


def _build_qdrant_settings(settings: APISettings) -> Any:
    from foldmind_ai_core.adapters.outbound.qdrant.settings import QdrantSettings

    return QdrantSettings(
        url=settings.required_qdrant_url,
        api_key=settings.qdrant_api_key_value,
    )


def _qdrant_collection_client(
    *,
    settings: Any,
    config: Any,
) -> Any:
    from foldmind_ai_core.adapters.outbound.qdrant.client import QdrantCollectionClient

    client = QdrantCollectionClient(settings=settings, config=config)
    client.setup_collection()
    return client


def _build_projection_ledger(settings: APISettings) -> Any:
    from foldmind_ai_core.adapters.outbound.postgres.client import PostgresClient
    from foldmind_ai_core.adapters.outbound.postgres.projection_ledger_repository import (
        PostgresProjectionLedgerRepository,
    )
    from foldmind_ai_core.adapters.outbound.postgres.settings import PostgresSettings

    return PostgresProjectionLedgerRepository(
        client=PostgresClient(
            settings=PostgresSettings(dsn=settings.required_postgres_dsn),
        ),
    )


def _build_source_freshness_checker(settings: APISettings) -> Any:
    from foldmind_ai_core.adapters.outbound.postgres.client import PostgresClient
    from foldmind_ai_core.adapters.outbound.postgres.settings import PostgresSettings
    from foldmind_ai_core.adapters.outbound.postgres.source_freshness_repository import (
        PostgresSourceFreshnessRepository,
    )

    return PostgresSourceFreshnessRepository(
        client=PostgresClient(
            settings=PostgresSettings(dsn=settings.required_postgres_dsn),
        ),
    )


def _build_neo4j_store(settings: APISettings) -> GraphStore:
    from foldmind_ai_core.adapters.outbound.neo4j.client import Neo4jClient
    from foldmind_ai_core.adapters.outbound.neo4j.settings import (
        Neo4jSettings,
    )
    from foldmind_ai_core.adapters.outbound.neo4j.stores.graph_store import (
        Neo4jGraphStore,
    )

    neo4j_settings = Neo4jSettings(
        uri=settings.required_neo4j_uri,
        username=settings.required_neo4j_user,
        password=settings.required_neo4j_password,
        database=settings.neo4j_database,
    )
    client = Neo4jClient(settings=neo4j_settings)
    client.ensure_database_schema()
    return Neo4jGraphStore(client=client)
