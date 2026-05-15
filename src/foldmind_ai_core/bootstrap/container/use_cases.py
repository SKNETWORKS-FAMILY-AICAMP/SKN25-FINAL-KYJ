from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from foldmind_ai_core.adapters.outbound.workflow_runtime.graph import LangGraphWorkflowGraph
from foldmind_ai_core.application.agents.answer_generator_agent import AnswerGeneratorAgent
from foldmind_ai_core.application.agents.chunk_relevance_validator_agent import (
    ChunkRelevanceValidatorAgent,
)
from foldmind_ai_core.application.agents.document_profiler_agent import DocumentProfilerAgent
from foldmind_ai_core.application.services.document_chunker import (
    DocumentChunker,
    DocumentChunkingConfig,
)
from foldmind_ai_core.application.services.document_retrieval_policy import (
    HybridSearchConfig,
)
from foldmind_ai_core.application.services.document_retrieval_service import (
    DocumentRetrievalService,
)
from foldmind_ai_core.application.services.folder_retrieval_service import (
    FolderRetrievalService,
)
from foldmind_ai_core.application.services.relationship_scope_resolver import (
    RelationshipScopeResolver,
)
from foldmind_ai_core.application.ports.outbound.prompt_repository import PromptRepositoryPort
from foldmind_ai_core.application.use_cases.indexing import (
    DeleteDocumentIndexUseCase,
    DeleteFolderIndexUseCase,
    IndexDocumentUseCase,
    IndexFolderUseCase,
)
from foldmind_ai_core.application.use_cases.recommendation.find_folders import FindFoldersUseCase
from foldmind_ai_core.application.use_cases.recommendation.recommend_folder import (
    RecommendFolderUseCase,
)
from foldmind_ai_core.application.use_cases.retrieval.answer_question import AnswerQuestionUseCase
from foldmind_ai_core.application.use_cases.retrieval.find_documents import (
    FindDocumentsUseCase,
)
from foldmind_ai_core.application.use_cases.workflow.get_task import GetTaskUseCase
from foldmind_ai_core.application.use_cases.workflow.record_action_result import (
    RecordActionResultUseCase,
)
from foldmind_ai_core.application.use_cases.workflow.remove_task_request import (
    RemoveTaskRequestUseCase,
)
from foldmind_ai_core.application.use_cases.workflow.run_task import RunTaskUseCase
from foldmind_ai_core.bootstrap.app_factory import APIUseCases, create_app
from foldmind_ai_core.bootstrap.container.checkpointing import build_workflow_checkpointer
from foldmind_ai_core.bootstrap.container.dependencies import (
    AICoreDependencies,
    AIProviderAdapters,
    RepositoryAdapter,
)
from foldmind_ai_core.bootstrap.container.providers import (
    build_ai_provider,
    build_prompt_repository,
)
from foldmind_ai_core.bootstrap.container.repositories import build_repository_adapter
from foldmind_ai_core.bootstrap.container.workflow import _build_workflow_engine
from foldmind_ai_core.bootstrap.settings import APISettings


def build_use_cases(
    dependencies: AICoreDependencies,
    *,
    settings: APISettings | None = None,
    hybrid_search_config: HybridSearchConfig | None = None,
    workflow_checkpointer: Any | None = None,
) -> APIUseCases:
    settings = settings or APISettings()
    ai = dependencies.ai
    repositories = dependencies.repositories
    relationship_scope_resolver = RelationshipScopeResolver(graph=repositories.graph)
    document_retrieval = DocumentRetrievalService(
        embeddings=ai.embeddings,
        chunk_vectors=repositories.chunk_vectors,
        document_vectors=repositories.document_vectors,
        graph=repositories.graph,
        keyword_repository=repositories.keyword_repository,
        config=hybrid_search_config or HybridSearchConfig(),
    )
    find_documents = FindDocumentsUseCase(
        retrieval=document_retrieval,
        scope_resolver=relationship_scope_resolver,
        result_filter=ChunkRelevanceValidatorAgent(
            llm=ai.llm,
            prompt_repository=dependencies.prompt_repository,
        ),
    )
    answer_generator = AnswerGeneratorAgent(
        llm=ai.llm,
        prompt_repository=dependencies.prompt_repository,
    )
    find_folders = FindFoldersUseCase(
        retrieval=FolderRetrievalService(
            embeddings=ai.embeddings,
            chunk_vectors=repositories.chunk_vectors,
            document_vectors=repositories.document_vectors,
            folder_vectors=repositories.folder_vectors,
            graph=repositories.graph,
        ),
        scope_resolver=relationship_scope_resolver,
    )
    recommend_folder = RecommendFolderUseCase(find_folders=find_folders)
    workflow = LangGraphWorkflowGraph(
        engine=_build_workflow_engine(
            llm=ai.llm,
            prompt_repository=dependencies.prompt_repository,
            find_documents=find_documents,
            find_folders=find_folders,
            recommend_folder=recommend_folder,
            answer_generator=answer_generator,
        ),
        checkpointer=workflow_checkpointer or build_workflow_checkpointer(settings),
    )
    return APIUseCases(
        index_document=IndexDocumentUseCase(
            indexing_uow=repositories.indexing_uow,
            profiler=DocumentProfilerAgent(
                llm=ai.llm,
                prompt_repository=dependencies.prompt_repository,
                profile_version=settings.required_profile_version,
                profile_schema_version=settings.required_profile_schema_version,
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
            indexing_uow=repositories.indexing_uow,
        ),
        index_folder=IndexFolderUseCase(
            indexing_uow=repositories.indexing_uow,
        ),
        delete_folder_index=DeleteFolderIndexUseCase(
            indexing_uow=repositories.indexing_uow,
        ),
        run_task=RunTaskUseCase(
            task_repository=repositories.task_repository,
            workflow=workflow,
        ),
        get_task=GetTaskUseCase(task_repository=repositories.task_repository),
        remove_task_request=RemoveTaskRequestUseCase(
            task_repository=repositories.task_repository,
            workflow=workflow,
        ),
        record_action_result=RecordActionResultUseCase(
            task_repository=repositories.task_repository,
            workflow=workflow,
        ),
        search_documents=find_documents,
        answer_question=AnswerQuestionUseCase(
            find_documents=find_documents,
            answer_generator=answer_generator,
        ),
        recommend_folder=recommend_folder,
    )


def build_app(
    dependencies: AICoreDependencies,
    *,
    settings: APISettings | None = None,
    hybrid_search_config: HybridSearchConfig | None = None,
    workflow_checkpointer: Any | None = None,
) -> FastAPI:
    settings = settings or APISettings()
    return create_app(
        build_use_cases(
            dependencies,
            settings=settings,
            hybrid_search_config=hybrid_search_config,
            workflow_checkpointer=workflow_checkpointer,
        ),
        settings=settings,
    )


def build_configured_app(
    *,
    settings: APISettings | None = None,
    repository_adapter: RepositoryAdapter | None = None,
    ai_provider_adapters: AIProviderAdapters | None = None,
    prompt_repository: PromptRepositoryPort | None = None,
    hybrid_search_config: HybridSearchConfig | None = None,
    workflow_checkpointer: Any | None = None,
) -> FastAPI:
    settings = settings or APISettings()
    ai_adapters = ai_provider_adapters or build_ai_provider(settings)
    repositories = repository_adapter or build_repository_adapter(settings)
    prompts = prompt_repository or build_prompt_repository(settings)
    return build_app(
        AICoreDependencies(
            ai=ai_adapters,
            repositories=repositories,
            prompt_repository=prompts,
        ),
        settings=settings,
        hybrid_search_config=hybrid_search_config,
        workflow_checkpointer=workflow_checkpointer,
    )
