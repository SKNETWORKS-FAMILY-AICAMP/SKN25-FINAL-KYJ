from __future__ import annotations

from dataclasses import dataclass

from ai_core.application.models.llm import LLMMessage
from ai_core.application.models.queries import AIQuery
from ai_core.application.models.results import GeneratedTextResult
from ai_core.application.ports.document_vector_store import DocumentVectorStore
from ai_core.application.ports.embedding import EmbeddingProvider
from ai_core.application.ports.llm import LLM
from ai_core.application.use_cases.hybrid_search import HybridSearchUseCase
from ai_core.common.validation import InvalidInputError


@dataclass(slots=True)
class AnswerQuestionUseCase:
    embeddings: EmbeddingProvider
    documents: DocumentVectorStore
    llm: LLM
    hybrid_search: HybridSearchUseCase | None = None
    top_k: int = 5

    def execute(self, query: AIQuery) -> GeneratedTextResult:
        if self.hybrid_search is not None:
            results = self.hybrid_search.execute(query)
        else:
            if query.request_context is None:
                raise InvalidInputError("request_context.tenant is required.")
            tenant = query.request_context.tenant
            vector = self.embeddings.embed_texts([query.text])[0]
            results = self.documents.similarity_search(
                tenant=tenant,
                query_vector=vector,
                top_k=self.top_k,
                scope=query.scope,
            )
        context = "\n\n".join(result.chunk.text for result in results)
        answer = self.llm.generate(
            [
                LLMMessage(
                    role="system",
                    content="Answer using only the provided FoldMind document context.",
                ),
                LLMMessage(role="user", content=f"Context:\n{context}\n\nQuestion:\n{query.text}"),
            ]
        )
        return GeneratedTextResult(text=answer, citations=results)
