from __future__ import annotations

from collections.abc import Callable

from dependency_injector import containers, providers

from foldmind_ai_core.adapters.outbound.postgres.client import PostgresClient
from foldmind_ai_core.adapters.outbound.postgres.retrieval_read_session import (
    PostgresRetrievalReadSessionProvider,
)
from foldmind_ai_core.adapters.outbound.postgres.indexing_write_session import (
    PostgresIndexingWriteSessionProvider,
)
from foldmind_ai_core.adapters.outbound.postgres.policies.retention_policy import (
    PurgeAfterPolicy,
)
from foldmind_ai_core.adapters.outbound.postgres.settings import PostgresSettings
from foldmind_ai_core.adapters.outbound.postgres.task_session import (
    PostgresTaskSessionProvider,
)
from foldmind_ai_core.bootstrap.api_services import APIApplicationServices
from foldmind_ai_core.bootstrap.app_factory import create_app
from foldmind_ai_core.bootstrap.container.checkpointing import (
    close_workflow_checkpointer_contexts,
)
from foldmind_ai_core.bootstrap.container.lifecycle import (
    ShutdownCallback,
    lazy_shutdown_callbacks_for,
)
from foldmind_ai_core.bootstrap.container.providers import (
    _build_ai_providers,
    _build_prompt_store,
)
from foldmind_ai_core.bootstrap.container.storage import (
    _build_neo4j_store,
    _build_qdrant_document_chunk_vector_store,
    _build_qdrant_document_vector_store,
    _build_qdrant_folder_vector_store,
    _build_qdrant_signal_vector_store,
)
from foldmind_ai_core.bootstrap.container.workflow import _build_workflow_runtime
from foldmind_ai_core.bootstrap.observability import (
    TracedApplicationService,
    TracedSessionProvider,
    TracedTransactionProvider,
)
from foldmind_ai_core.bootstrap.settings import APISettings
from foldmind_ai_core.core.application.agents.context_generation_agent import (
    ContextGenerationAgent,
)
from foldmind_ai_core.core.application.agents.document_signal_extractor_agent import (
    DocumentSignalExtractorAgent,
)
from foldmind_ai_core.core.application.services.indexing.document_indexing_service import (
    DocumentIndexingService,
)
from foldmind_ai_core.core.application.services.indexing.folder_indexing_service import (
    FolderIndexingService,
)
from foldmind_ai_core.core.application.services.recommendation.folder_recommendation_service import (  # noqa: E501
    FolderRecommendationService,
)
from foldmind_ai_core.core.application.services.recommendation.folder_recommendation_source_resolver import (  # noqa: E501
    FolderRecommendationSourceResolver,
)
from foldmind_ai_core.core.application.services.retrieval.document_retrieval_service import (
    DocumentRetrievalService,
)
from foldmind_ai_core.core.application.services.retrieval.document_search_service import (
    DocumentSearchService,
)
from foldmind_ai_core.core.application.services.retrieval.folder_retrieval_service import (
    FolderRetrievalService,
)
from foldmind_ai_core.core.application.services.retrieval.folder_search_service import (
    FolderSearchService,
)
from foldmind_ai_core.core.application.services.retrieval.policy import (
    DocumentRetrievalConfig,
)
from foldmind_ai_core.core.application.services.retrieval.scope_resolver import (
    RelationshipScopeResolver,
)
from foldmind_ai_core.core.application.services.retrieval.signal_retrieval_service import (
    SignalRetrievalService,
)
from foldmind_ai_core.core.application.services.retrieval.signal_search_service import (
    SignalSearchService,
)
from foldmind_ai_core.core.application.services.workflow.task_workflow_service import (
    TaskWorkflowService,
)
from foldmind_ai_core.core.application.models.vector_projection import VectorProjectionSpec
from foldmind_ai_core.core.domain.models.document_chunks import (
    DocumentChunkingPolicy,
    DocumentIndexingPolicy,
)
from foldmind_ai_core.core.domain.services.document_chunker import DocumentChunker


def _application_shutdown_callbacks(
    *,
    postgres_client_provider: Callable[[], object],
    chunk_vectors_provider: Callable[[], object],
    document_vectors_provider: Callable[[], object],
    signal_vectors_provider: Callable[[], object],
    folder_vectors_provider: Callable[[], object],
    graph_provider: Callable[[], object],
) -> tuple[ShutdownCallback, ...]:
    return (
        *lazy_shutdown_callbacks_for(
            postgres_client_provider,
            chunk_vectors_provider,
            document_vectors_provider,
            signal_vectors_provider,
            folder_vectors_provider,
            graph_provider,
        ),
        close_workflow_checkpointer_contexts,
    )


class ApplicationContainer(containers.DeclarativeContainer):  # type: ignore[misc]
    settings = providers.Singleton(APISettings)
    document_retrieval_config = providers.Factory(DocumentRetrievalConfig)
    workflow_checkpointer = providers.Object(None)

    ai = providers.Singleton(_build_ai_providers, settings=settings)
    prompt_store = providers.Singleton(_build_prompt_store, settings=settings)

    postgres_settings = providers.Factory(
        PostgresSettings,
        dsn=settings.provided.required_postgres_dsn,
    )
    postgres_client = providers.Singleton(PostgresClient, settings=postgres_settings)
    purge_after_policy = providers.Singleton(
        PurgeAfterPolicy,
        days=settings.provided.purge_after_days,
    )
    indexing = providers.Singleton(
        TracedTransactionProvider,
        wrapped=providers.Singleton(
            PostgresIndexingWriteSessionProvider,
            sessions=postgres_client,
            purge_after_policy=purge_after_policy,
        ),
        span_name="postgres.transaction.indexing",
    )
    retrieval_reads = providers.Singleton(
        TracedSessionProvider,
        wrapped=providers.Singleton(
            PostgresRetrievalReadSessionProvider,
            sessions=postgres_client,
        ),
        span_name="postgres.retrieval_read",
    )
    tasks = providers.Singleton(
        TracedSessionProvider,
        wrapped=providers.Singleton(PostgresTaskSessionProvider, sessions=postgres_client),
        span_name="postgres.task",
    )
    chunk_vectors = providers.Singleton(
        _build_qdrant_document_chunk_vector_store,
        settings=settings,
    )
    document_vectors = providers.Singleton(
        _build_qdrant_document_vector_store,
        settings=settings,
    )
    signal_vectors = providers.Singleton(
        _build_qdrant_signal_vector_store,
        settings=settings,
    )
    folder_vectors = providers.Singleton(
        _build_qdrant_folder_vector_store,
        settings=settings,
    )
    graph = providers.Singleton(_build_neo4j_store, settings=settings)

    relationship_scope_resolver = providers.Factory(
        RelationshipScopeResolver,
        graph=graph,
    )
    document_retrieval = providers.Factory(
        DocumentRetrievalService,
        embeddings=ai.provided.embeddings,
        chunk_vectors=chunk_vectors,
        document_vectors=document_vectors,
        graph=graph,
        retrieval_reads=retrieval_reads,
        config=document_retrieval_config,
    )
    document_search = providers.Factory(
        DocumentSearchService,
        retrieval=document_retrieval,
        scope_resolver=relationship_scope_resolver,
    )
    signal_search = providers.Factory(
        SignalSearchService,
        retrieval=providers.Factory(
            SignalRetrievalService,
            embeddings=ai.provided.embeddings,
            signal_vectors=signal_vectors,
        ),
    )
    context_generator = providers.Factory(
        ContextGenerationAgent,
        llm=ai.provided.llm,
        prompt_store=prompt_store,
    )
    folder_search = providers.Factory(
        FolderSearchService,
        retrieval=providers.Factory(
            FolderRetrievalService,
            embeddings=ai.provided.embeddings,
            chunk_vectors=chunk_vectors,
            document_vectors=document_vectors,
            folder_vectors=folder_vectors,
            graph=graph,
            retrieval_reads=retrieval_reads,
        ),
        scope_resolver=relationship_scope_resolver,
    )
    folder_recommendation = providers.Factory(
        FolderRecommendationService,
        folder_search=folder_search,
    )
    folder_recommendation_sources = providers.Factory(
        FolderRecommendationSourceResolver,
        retrieval_reads=retrieval_reads,
        graph=graph,
    )
    workflow = providers.Factory(
        _build_workflow_runtime,
        settings=settings,
        llm=ai.provided.llm,
        prompt_store=prompt_store,
        document_search=document_search,
        signal_search=signal_search,
        folder_search=folder_search,
        folder_recommendation=folder_recommendation,
        folder_recommendation_sources=folder_recommendation_sources,
        context_generator=context_generator,
        checkpointer=workflow_checkpointer,
    )
    document_chunker = providers.Factory(
        DocumentChunker,
        providers.Factory(
            DocumentIndexingPolicy,
            chunking=providers.Factory(
                DocumentChunkingPolicy,
                chunking_version=settings.provided.required_chunking_version,
            ),
            index_schema_version=settings.provided.required_index_schema_version,
        ),
    )
    vector_projection_spec = providers.Factory(
        VectorProjectionSpec,
        embedding_model=settings.provided.required_embedding_model,
        embedding_version=settings.provided.required_embedding_version,
        index_schema_version=settings.provided.required_index_schema_version,
    )
    document_signal_extractor = providers.Factory(
        DocumentSignalExtractorAgent,
        llm=ai.provided.llm,
        prompt_store=prompt_store,
        prompt_version=settings.provided.required_document_signal_extraction_prompt_version,
        model=settings.provided.llm_model,
    )
    document_indexing_service = providers.Factory(
        DocumentIndexingService,
        indexing=indexing,
        signal_extractor=document_signal_extractor,
        chunker=document_chunker,
        vector_projection_spec=vector_projection_spec,
    )
    folder_indexing_service = providers.Factory(
        FolderIndexingService,
        indexing=indexing,
    )
    document_indexing = providers.Factory(
        TracedApplicationService,
        wrapped=document_indexing_service,
        service_name="document_indexing",
    )
    folder_indexing = providers.Factory(
        TracedApplicationService,
        wrapped=folder_indexing_service,
        service_name="folder_indexing",
    )
    task_workflow_service = providers.Factory(
        TaskWorkflowService,
        tasks=tasks,
        workflow=workflow,
    )
    task_workflow = providers.Factory(
        TracedApplicationService,
        wrapped=task_workflow_service,
        service_name="task_workflow",
    )

    api_services = providers.Factory(
        APIApplicationServices,
        document_indexing=document_indexing,
        folder_indexing=folder_indexing,
        task_workflow=task_workflow,
    )
    shutdown_callbacks = providers.Callable(
        _application_shutdown_callbacks,
        postgres_client_provider=providers.Object(postgres_client),
        chunk_vectors_provider=providers.Object(chunk_vectors),
        document_vectors_provider=providers.Object(document_vectors),
        signal_vectors_provider=providers.Object(signal_vectors),
        folder_vectors_provider=providers.Object(folder_vectors),
        graph_provider=providers.Object(graph),
    )
    fastapi_app = providers.Factory(
        create_app,
        application_services=api_services,
        settings=settings,
        shutdown_callbacks=shutdown_callbacks,
    )
