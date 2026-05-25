from __future__ import annotations

from typing import Any

from foldmind_ai_core.bootstrap.settings import APISettings
from foldmind_ai_core.core.application.ports.outbound.store.graph_store import GraphStore
from foldmind_ai_core.core.application.ports.outbound.store.vector_store import (
    DocumentChunkVectorStore,
    DocumentVectorStore,
    FolderVectorStore,
    SignalVectorStore,
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

    if qdrant_settings is None:
        qdrant_settings = _build_qdrant_settings(settings)
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

    if qdrant_settings is None:
        qdrant_settings = _build_qdrant_settings(settings)
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

    if qdrant_settings is None:
        qdrant_settings = _build_qdrant_settings(settings)
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

    if qdrant_settings is None:
        qdrant_settings = _build_qdrant_settings(settings)
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
                    "parent_folder_id",
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
