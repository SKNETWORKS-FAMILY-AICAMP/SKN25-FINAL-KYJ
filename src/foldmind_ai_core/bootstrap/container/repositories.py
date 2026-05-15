from __future__ import annotations

from typing import Any

from foldmind_ai_core.application.ports.outbound.graph_repository import GraphRepository
from foldmind_ai_core.application.ports.outbound.indexing_unit_of_work import (
    IndexingUnitOfWork,
)
from foldmind_ai_core.application.ports.outbound.profile_repository import ProfileRepository
from foldmind_ai_core.application.ports.outbound.task_repository import TaskRepository
from foldmind_ai_core.application.ports.outbound.vector_repository import (
    DocumentChunkVectorRepository,
    DocumentVectorRepository,
    FolderVectorRepository,
)
from foldmind_ai_core.bootstrap.container.dependencies import (
    OutboxProjectionRepositoryAdapter,
    RepositoryAdapter,
)
from foldmind_ai_core.bootstrap.settings import APISettings, OutboxProjectionTarget


def build_repository_adapter(settings: APISettings) -> RepositoryAdapter:
    settings.require_configured_storage()

    (
        task_repository,
        profile_repository,
        indexing_uow,
    ) = _build_postgres_repositories(settings)
    chunk_vectors, document_vectors, folder_vectors = _build_qdrant_repositories(settings)
    graph = _build_neo4j_repository(settings)

    return RepositoryAdapter(
        task_repository=task_repository,
        profile_repository=profile_repository,
        indexing_uow=indexing_uow,
        chunk_vectors=chunk_vectors,
        document_vectors=document_vectors,
        folder_vectors=folder_vectors,
        graph=graph,
        keyword_repository=None,
    )


def build_outbox_projection_repository_adapter(
    settings: APISettings,
    *,
    target: OutboxProjectionTarget,
) -> OutboxProjectionRepositoryAdapter:
    if target is OutboxProjectionTarget.QDRANT_DOCUMENT_CHUNKS:
        return OutboxProjectionRepositoryAdapter(
            chunk_vectors=_build_qdrant_document_chunk_vector_repository(settings),
        )
    if target is OutboxProjectionTarget.QDRANT_DOCUMENTS:
        return OutboxProjectionRepositoryAdapter(
            document_vectors=_build_qdrant_document_vector_repository(settings),
        )
    if target is OutboxProjectionTarget.QDRANT_FOLDERS:
        return OutboxProjectionRepositoryAdapter(
            folder_vectors=_build_qdrant_folder_vector_repository(settings),
        )
    if target is OutboxProjectionTarget.NEO4J_GRAPH:
        return OutboxProjectionRepositoryAdapter(graph=_build_neo4j_repository(settings))
    raise RuntimeError(f"Unsupported OUTBOX_PROJECTION_TARGET: {target}")


def _build_postgres_repositories(
    settings: APISettings,
) -> tuple[
    TaskRepository,
    ProfileRepository,
    IndexingUnitOfWork,
]:
    from foldmind_ai_core.adapters.outbound.postgres.client import PostgresClient
    from foldmind_ai_core.adapters.outbound.postgres.indexing_unit_of_work import (
        PostgresIndexingUnitOfWork,
    )
    from foldmind_ai_core.adapters.outbound.postgres.outbox_repository import (
        PostgresOutboxRepository,
    )
    from foldmind_ai_core.adapters.outbound.postgres.profile_repository import (
        PostgresProfileRepository,
    )
    from foldmind_ai_core.adapters.outbound.postgres.settings import PostgresSettings
    from foldmind_ai_core.adapters.outbound.postgres.task_repository import (
        PostgresTaskRepository,
    )

    postgres_dsn = settings.required_postgres_dsn
    postgres_client = PostgresClient(settings=PostgresSettings(dsn=postgres_dsn))
    profile_repository = PostgresProfileRepository(client=postgres_client)
    outbox_repository = PostgresOutboxRepository(client=postgres_client)
    return (
        PostgresTaskRepository(client=postgres_client),
        profile_repository,
        PostgresIndexingUnitOfWork(
            client=postgres_client,
            profile_repository=profile_repository,
            outbox_repository=outbox_repository,
        ),
    )


def _build_qdrant_repositories(
    settings: APISettings,
) -> tuple[
    DocumentChunkVectorRepository,
    DocumentVectorRepository,
    FolderVectorRepository,
]:
    qdrant_settings = _build_qdrant_settings(settings)
    return (
        _build_qdrant_document_chunk_vector_repository(
            settings,
            qdrant_settings=qdrant_settings,
        ),
        _build_qdrant_document_vector_repository(
            settings,
            qdrant_settings=qdrant_settings,
        ),
        _build_qdrant_folder_vector_repository(
            settings,
            qdrant_settings=qdrant_settings,
        ),
    )


def _build_qdrant_document_chunk_vector_repository(
    settings: APISettings,
    *,
    qdrant_settings: Any | None = None,
) -> DocumentChunkVectorRepository:
    from foldmind_ai_core.adapters.outbound.qdrant.client import (
        QdrantCollectionConfig,
    )
    from foldmind_ai_core.adapters.outbound.qdrant.document_chunk_vector_repository import (
        QdrantDocumentChunkVectorRepository,
    )

    qdrant_settings = qdrant_settings or _build_qdrant_settings(settings)
    return QdrantDocumentChunkVectorRepository(
        client=_qdrant_collection_client(
            settings=qdrant_settings,
            config=QdrantCollectionConfig(
                collection_name=settings.qdrant_document_chunk_collection,
                vector_size=settings.qdrant_vector_size,
                distance=settings.qdrant_distance,
                payload_indexes=(
                    "tenant",
                    "document_id",
                    "document_type",
                    "chunk_id",
                    "source_version",
                ),
            ),
        )
    )


def _build_qdrant_document_vector_repository(
    settings: APISettings,
    *,
    qdrant_settings: Any | None = None,
) -> DocumentVectorRepository:
    from foldmind_ai_core.adapters.outbound.qdrant.client import (
        QdrantCollectionConfig,
    )
    from foldmind_ai_core.adapters.outbound.qdrant.document_vector_repository import (
        QdrantDocumentVectorRepository,
    )

    qdrant_settings = qdrant_settings or _build_qdrant_settings(settings)
    return QdrantDocumentVectorRepository(
        client=_qdrant_collection_client(
            settings=qdrant_settings,
            config=QdrantCollectionConfig(
                collection_name=settings.qdrant_document_collection,
                vector_size=settings.qdrant_vector_size,
                distance=settings.qdrant_distance,
                payload_indexes=(
                    "tenant",
                    "document_id",
                    "document_type",
                    "source_version",
                    "concept_ids",
                    "profile_version",
                    "profile_schema_version",
                ),
            ),
        )
    )


def _build_qdrant_folder_vector_repository(
    settings: APISettings,
    *,
    qdrant_settings: Any | None = None,
) -> FolderVectorRepository:
    from foldmind_ai_core.adapters.outbound.qdrant.client import (
        QdrantCollectionConfig,
    )
    from foldmind_ai_core.adapters.outbound.qdrant.folder_vector_repository import (
        QdrantFolderVectorRepository,
    )

    qdrant_settings = qdrant_settings or _build_qdrant_settings(settings)
    return QdrantFolderVectorRepository(
        client=_qdrant_collection_client(
            settings=qdrant_settings,
            config=QdrantCollectionConfig(
                collection_name=settings.qdrant_folder_collection,
                vector_size=settings.qdrant_vector_size,
                distance=settings.qdrant_distance,
                payload_indexes=(
                    "tenant",
                    "folder_id",
                    "source_version",
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


def _build_neo4j_repository(settings: APISettings) -> GraphRepository:
    from foldmind_ai_core.adapters.outbound.neo4j.client import Neo4jClient
    from foldmind_ai_core.adapters.outbound.neo4j.graph_repository import (
        Neo4jGraphRepository,
    )
    from foldmind_ai_core.adapters.outbound.neo4j.settings import (
        Neo4jSettings,
    )

    neo4j_settings = Neo4jSettings(
        uri=settings.required_neo4j_uri,
        username=settings.required_neo4j_user,
        password=settings.required_neo4j_password,
        database=settings.neo4j_database,
    )
    client = Neo4jClient(settings=neo4j_settings)
    client.ensure_database_schema()
    return Neo4jGraphRepository(client=client)
