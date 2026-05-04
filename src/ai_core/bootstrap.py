from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI

from ai_core.agents.answer_generator import AnswerGeneratorAgent
from ai_core.agents.folder_recommender import FolderRecommenderAgent
from ai_core.agents.search_agent import HybridSearchConfig, SearchAgent
from ai_core.api.app import APIUseCases, create_app
from ai_core.api.settings import APISettings
from ai_core.application.ports.document_keyword_store import DocumentKeywordSearchStore
from ai_core.application.ports.document_vector_store import DocumentVectorStore
from ai_core.application.ports.embedding import EmbeddingProvider
from ai_core.application.ports.folder_vector_store import FolderVectorStore
from ai_core.application.ports.llm import LLM
from ai_core.application.ports.task_store import TaskStore
from ai_core.application.use_cases.answer_question import AnswerQuestionUseCase
from ai_core.application.use_cases.delete_document_index import DeleteDocumentIndexUseCase
from ai_core.application.use_cases.hybrid_search import HybridSearchUseCase
from ai_core.application.use_cases.index_document import IndexDocumentUseCase
from ai_core.application.use_cases.recommend_folder import RecommendFolderUseCase
from ai_core.application.use_cases.record_action_result import RecordActionResultUseCase
from ai_core.application.use_cases.run_task import RunTaskUseCase


@dataclass(slots=True)
class AICoreDependencies:
    embeddings: EmbeddingProvider
    document_vectors: DocumentVectorStore
    document_keywords: DocumentKeywordSearchStore
    folder_vectors: FolderVectorStore
    llm: LLM
    tasks: TaskStore


def build_use_cases(
    dependencies: AICoreDependencies,
    *,
    hybrid_search_config: HybridSearchConfig | None = None,
) -> APIUseCases:
    search_agent = SearchAgent(
        embeddings=dependencies.embeddings,
        documents=dependencies.document_vectors,
        keywords=dependencies.document_keywords,
        config=hybrid_search_config or HybridSearchConfig(),
    )
    hybrid_search = HybridSearchUseCase(search=search_agent)
    return APIUseCases(
        index_document=IndexDocumentUseCase(
            embeddings=dependencies.embeddings,
            documents=dependencies.document_vectors,
            keywords=dependencies.document_keywords,
        ),
        delete_document_index=DeleteDocumentIndexUseCase(
            documents=dependencies.document_vectors,
            keywords=dependencies.document_keywords,
        ),
        run_task=RunTaskUseCase(tasks=dependencies.tasks),
        record_action_result=RecordActionResultUseCase(tasks=dependencies.tasks),
        search_documents=hybrid_search,
        answer_question=AnswerQuestionUseCase(
            search=search_agent,
            answer_generator=AnswerGeneratorAgent(llm=dependencies.llm),
        ),
        recommend_folder=RecommendFolderUseCase(
            folder_recommender=FolderRecommenderAgent(
                embeddings=dependencies.embeddings,
                folders=dependencies.folder_vectors,
            ),
        ),
    )


def build_app(
    dependencies: AICoreDependencies,
    *,
    settings: APISettings | None = None,
    hybrid_search_config: HybridSearchConfig | None = None,
) -> FastAPI:
    return create_app(
        build_use_cases(
            dependencies,
            hybrid_search_config=hybrid_search_config,
        ),
        settings=settings,
    )
