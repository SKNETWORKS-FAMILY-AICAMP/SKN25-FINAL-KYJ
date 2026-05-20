from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.ports.outbound.embedding import EmbeddingProvider
from foldmind_ai_core.core.application.ports.outbound.graph_store import GraphStore
from foldmind_ai_core.core.application.ports.outbound.indexed_document_source import (
    IndexedDocumentSourceRepository,
)
from foldmind_ai_core.core.application.ports.outbound.indexing_unit_of_work import (
    IndexingUnitOfWork,
)
from foldmind_ai_core.core.application.ports.outbound.llm import LLMProvider
from foldmind_ai_core.core.application.ports.outbound.projection_ledger import (
    ProjectionLedger,
)
from foldmind_ai_core.core.application.ports.outbound.prompt_store import PromptStore
from foldmind_ai_core.core.application.ports.outbound.source_freshness import (
    SourceFreshnessChecker,
)
from foldmind_ai_core.core.application.ports.outbound.task_repository import TaskRepository
from foldmind_ai_core.core.application.ports.outbound.vector_store import (
    DocumentChunkVectorStore,
    DocumentVectorStore,
    FolderVectorStore,
    SignalVectorStore,
)


@dataclass(slots=True)
class ApplicationStorage:
    task_repository: TaskRepository
    indexing_uow: IndexingUnitOfWork
    indexed_document_sources: IndexedDocumentSourceRepository
    chunk_vectors: DocumentChunkVectorStore
    document_vectors: DocumentVectorStore
    folder_vectors: FolderVectorStore
    graph: GraphStore
    signal_vectors: SignalVectorStore


@dataclass(slots=True)
class OutboxProjectionStorage:
    chunk_vectors: DocumentChunkVectorStore | None = None
    document_vectors: DocumentVectorStore | None = None
    signal_vectors: SignalVectorStore | None = None
    folder_vectors: FolderVectorStore | None = None
    graph: GraphStore | None = None
    projection_ledger: ProjectionLedger | None = None
    source_freshness: SourceFreshnessChecker | None = None


ProjectionStorage = ApplicationStorage | OutboxProjectionStorage


@dataclass(slots=True)
class AICapabilities:
    llm: LLMProvider
    embeddings: EmbeddingProvider


@dataclass(slots=True)
class ApplicationDependencies:
    ai: AICapabilities
    storage: ApplicationStorage
    prompt_store: PromptStore
