from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.ports.outbound.embedding import EmbeddingProvider
from foldmind_ai_core.application.ports.outbound.graph_repository import GraphRepository
from foldmind_ai_core.application.ports.outbound.indexing_unit_of_work import (
    IndexingUnitOfWork,
)
from foldmind_ai_core.application.ports.outbound.llm import LLM
from foldmind_ai_core.application.ports.outbound.profile_repository import ProfileRepository
from foldmind_ai_core.application.ports.outbound.prompt_repository import PromptRepositoryPort
from foldmind_ai_core.application.ports.outbound.task_repository import TaskRepository
from foldmind_ai_core.application.ports.outbound.vector_repository import (
    DocumentChunkVectorRepository,
    DocumentKeywordRepository,
    DocumentVectorRepository,
    FolderVectorRepository,
)


@dataclass(slots=True)
class RepositoryAdapter:
    task_repository: TaskRepository
    profile_repository: ProfileRepository
    indexing_uow: IndexingUnitOfWork
    chunk_vectors: DocumentChunkVectorRepository
    document_vectors: DocumentVectorRepository
    folder_vectors: FolderVectorRepository
    graph: GraphRepository
    keyword_repository: DocumentKeywordRepository | None = None


@dataclass(slots=True)
class OutboxProjectionRepositoryAdapter:
    chunk_vectors: DocumentChunkVectorRepository | None = None
    document_vectors: DocumentVectorRepository | None = None
    folder_vectors: FolderVectorRepository | None = None
    graph: GraphRepository | None = None


OutboxProjectionRepositories = RepositoryAdapter | OutboxProjectionRepositoryAdapter


@dataclass(slots=True)
class AIProviderAdapters:
    llm: LLM
    embeddings: EmbeddingProvider


@dataclass(slots=True)
class AICoreDependencies:
    ai: AIProviderAdapters
    repositories: RepositoryAdapter
    prompt_repository: PromptRepositoryPort
