from __future__ import annotations

from dataclasses import dataclass

from ai_core.application.ports.document_vector_store import DocumentVectorStore
from ai_core.application.ports.embedding import EmbeddingProvider
from ai_core.domain.chunks import RetrievalResult
from ai_core.domain.tasks import AIQuery


@dataclass(slots=True)
class SearchAgent:
    embeddings: EmbeddingProvider
    documents: DocumentVectorStore
    top_k: int = 5

    def search_documents(self, query: AIQuery) -> list[RetrievalResult]:
        tenant = query.request_context.tenant if query.request_context else ""
        vector = self.embeddings.embed_texts([query.text])[0]
        return self.documents.similarity_search(
            tenant=tenant,
            query_vector=vector,
            top_k=self.top_k,
            scope=query.scope,
        )
