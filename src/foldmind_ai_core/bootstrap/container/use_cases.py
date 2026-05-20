from __future__ import annotations

from typing import Any

from foldmind_ai_core.bootstrap.api_use_cases import APIUseCases
from foldmind_ai_core.bootstrap.container.dependencies import (
    ApplicationDependencies,
)
from foldmind_ai_core.bootstrap.container.workflow import build_workflow_runtime
from foldmind_ai_core.bootstrap.settings import APISettings
from foldmind_ai_core.core.application.agents.chunk_relevance_filter_agent import (
    ChunkRelevanceFilterAgent,
)
from foldmind_ai_core.core.application.agents.context_generation_agent import (
    ContextGenerationAgent,
)
from foldmind_ai_core.core.application.agents.document_profiler_agent import DocumentProfilerAgent
from foldmind_ai_core.core.application.services.document_retrieval_policy import (
    DocumentRetrievalConfig,
)
from foldmind_ai_core.core.application.services.document_retrieval_service import (
    DocumentRetrievalService,
)
from foldmind_ai_core.core.application.services.folder_recommendation_source_resolver import (
    FolderRecommendationSourceResolver,
)
from foldmind_ai_core.core.application.services.folder_retrieval_service import (
    FolderRetrievalService,
)
from foldmind_ai_core.core.application.services.relationship_scope_resolver import (
    RelationshipScopeResolver,
)
from foldmind_ai_core.core.application.services.signal_retrieval_service import (
    SignalRetrievalService,
)
from foldmind_ai_core.core.application.use_cases.indexing.delete_document_index import (
    DeleteDocumentIndexUseCase,
)
from foldmind_ai_core.core.application.use_cases.indexing.delete_folder_index import (
    DeleteFolderIndexUseCase,
)
from foldmind_ai_core.core.application.use_cases.indexing.index_document import (
    IndexDocumentUseCase,
)
from foldmind_ai_core.core.application.use_cases.indexing.index_folder import (
    IndexFolderUseCase,
)
from foldmind_ai_core.core.application.use_cases.indexing.update_document_folder_relations import (
    UpdateDocumentFolderRelationsUseCase,
)
from foldmind_ai_core.core.application.use_cases.recommendation.find_folders import (
    FindFoldersUseCase,
)
from foldmind_ai_core.core.application.use_cases.recommendation.recommend_folder import (
    RecommendFolderUseCase,
)
from foldmind_ai_core.core.application.use_cases.retrieval.find_documents import (
    FindDocumentsUseCase,
)
from foldmind_ai_core.core.application.use_cases.retrieval.find_signals import (
    FindSignalsUseCase,
)
from foldmind_ai_core.core.application.use_cases.workflow.get_task import GetTaskUseCase
from foldmind_ai_core.core.application.use_cases.workflow.record_action_result import (
    RecordActionResultUseCase,
)
from foldmind_ai_core.core.application.use_cases.workflow.remove_task_input import (
    RemoveTaskInputUseCase,
)
from foldmind_ai_core.core.application.use_cases.workflow.run_task import RunTaskUseCase
from foldmind_ai_core.core.domain.services.document_chunking import (
    DocumentChunker,
    DocumentChunkingConfig,
)


def build_use_cases(
    dependencies: ApplicationDependencies,
    *,
    settings: APISettings | None = None,
    document_retrieval_config: DocumentRetrievalConfig | None = None,
    workflow_checkpointer: Any | None = None,
) -> APIUseCases:
    settings = settings or APISettings()
    ai = dependencies.ai
    storage = dependencies.storage
    relationship_scope_resolver = RelationshipScopeResolver(graph=storage.graph)
    document_retrieval = DocumentRetrievalService(
        embeddings=ai.embeddings,
        chunk_vectors=storage.chunk_vectors,
        document_vectors=storage.document_vectors,
        graph=storage.graph,
        config=document_retrieval_config or DocumentRetrievalConfig(),
    )
    find_documents = FindDocumentsUseCase(
        retrieval=document_retrieval,
        scope_resolver=relationship_scope_resolver,
        result_filter=ChunkRelevanceFilterAgent(
            llm=ai.llm,
            prompt_store=dependencies.prompt_store,
        ),
    )
    find_signals = FindSignalsUseCase(
        retrieval=SignalRetrievalService(
            embeddings=ai.embeddings,
            signal_vectors=storage.signal_vectors,
        )
    )
    context_generator = ContextGenerationAgent(
        llm=ai.llm,
        prompt_store=dependencies.prompt_store,
    )
    find_folders = FindFoldersUseCase(
        retrieval=FolderRetrievalService(
            embeddings=ai.embeddings,
            chunk_vectors=storage.chunk_vectors,
            document_vectors=storage.document_vectors,
            folder_vectors=storage.folder_vectors,
            graph=storage.graph,
        ),
        scope_resolver=relationship_scope_resolver,
    )
    recommend_folder = RecommendFolderUseCase(find_folders=find_folders)
    folder_recommendation_sources = FolderRecommendationSourceResolver(
        indexed_documents=storage.indexed_document_sources,
        graph=storage.graph,
    )
    workflow = build_workflow_runtime(
        settings=settings,
        llm=ai.llm,
        prompt_store=dependencies.prompt_store,
        find_documents=find_documents,
        find_signals=find_signals,
        find_folders=find_folders,
        recommend_folder=recommend_folder,
        folder_recommendation_sources=folder_recommendation_sources,
        context_generator=context_generator,
        checkpointer=workflow_checkpointer,
    )
    return APIUseCases(
        index_document=IndexDocumentUseCase(
            indexing_uow=storage.indexing_uow,
            signal_extractor=DocumentProfilerAgent(
                llm=ai.llm,
                prompt_store=dependencies.prompt_store,
                prompt_version=settings.required_document_profile_prompt_version,
                model=settings.llm_model,
            ),
            chunker=DocumentChunker(
                DocumentChunkingConfig(
                    chunking_version=settings.required_chunking_version,
                    embedding_model=settings.required_embedding_model,
                    embedding_version=settings.required_embedding_version,
                    index_schema_version=settings.required_index_schema_version,
                )
            ),
        ),
        delete_document_index=DeleteDocumentIndexUseCase(
            indexing_uow=storage.indexing_uow,
        ),
        update_document_folder_relations=UpdateDocumentFolderRelationsUseCase(
            indexing_uow=storage.indexing_uow,
        ),
        index_folder=IndexFolderUseCase(
            indexing_uow=storage.indexing_uow,
        ),
        delete_folder_index=DeleteFolderIndexUseCase(
            indexing_uow=storage.indexing_uow,
        ),
        run_task=RunTaskUseCase(
            task_repository=storage.task_repository,
            workflow=workflow,
        ),
        get_task=GetTaskUseCase(task_repository=storage.task_repository),
        remove_task_input=RemoveTaskInputUseCase(
            task_repository=storage.task_repository,
            workflow=workflow,
        ),
        record_action_result=RecordActionResultUseCase(
            task_repository=storage.task_repository,
            workflow=workflow,
        ),
    )
