from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.ports.outbound.checker.source_freshness import (
    SourceFreshnessChecker,
)
from foldmind_ai_core.core.application.ports.outbound.provider.embedding import EmbeddingProvider
from foldmind_ai_core.core.application.ports.outbound.provider.llm import LLMProvider
from foldmind_ai_core.core.application.ports.outbound.session.projection_ledger_session import (
    ProjectionLedgerSessionProvider,
)
from foldmind_ai_core.core.application.ports.outbound.store.graph_store import GraphStore
from foldmind_ai_core.core.application.ports.outbound.store.vector_store import (
    DocumentChunkVectorStore,
    DocumentVectorStore,
    FolderVectorStore,
    SignalVectorStore,
)


@dataclass(slots=True)
class OutboxProjectionStorage:
    source_freshness: SourceFreshnessChecker
    chunk_vectors: DocumentChunkVectorStore | None = None
    document_vectors: DocumentVectorStore | None = None
    signal_vectors: SignalVectorStore | None = None
    folder_vectors: FolderVectorStore | None = None
    graph: GraphStore | None = None
    projection_ledger: ProjectionLedgerSessionProvider | None = None


@dataclass(slots=True)
class AIProviders:
    llm: LLMProvider
    embeddings: EmbeddingProvider
