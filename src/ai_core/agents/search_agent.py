from __future__ import annotations

from dataclasses import dataclass

from ai_core.application.ports.document_keyword_store import DocumentKeywordSearchStore
from ai_core.application.ports.document_vector_store import DocumentVectorStore
from ai_core.application.ports.embedding import EmbeddingProvider
from ai_core.application.use_cases.hybrid_search import HybridSearchConfig, HybridSearchUseCase
from ai_core.application.models.retrieval import RetrievalResult
from ai_core.application.models.queries import AIQuery


@dataclass(slots=True)
class SearchAgent:
    embeddings: EmbeddingProvider
    documents: DocumentVectorStore
    keywords: DocumentKeywordSearchStore | None = None
    top_k: int = 5
    hybrid_config: HybridSearchConfig | None = None

    def search_documents(self, query: AIQuery) -> list[RetrievalResult]:
        if self.keywords is not None:
            config = self.hybrid_config or HybridSearchConfig(top_k=self.top_k)
            return HybridSearchUseCase(
                embeddings=self.embeddings,
                documents=self.documents,
                keywords=self.keywords,
                config=config,
            ).execute(query)

        tenant = query.request_context.tenant if query.request_context else ""
        vector = self.embeddings.embed_texts([query.text])[0]
        return self.documents.similarity_search(
            tenant=tenant,
            query_vector=vector,
            top_k=self.top_k,
            scope=query.scope,
        )
