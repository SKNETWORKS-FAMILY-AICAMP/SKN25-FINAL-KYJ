from __future__ import annotations

from dataclasses import dataclass

from ai_core.application.models.llm import LLMMessage
from ai_core.application.models.queries import AIQuery
from ai_core.application.models.results import GeneratedTextResult
from ai_core.application.models.retrieval import RetrievalResult
from ai_core.application.ports.llm import LLM


@dataclass(slots=True)
class AnswerGeneratorAgent:
    llm: LLM

    def answer(self, *, query: AIQuery, citations: list[RetrievalResult]) -> GeneratedTextResult:
        context = "\n\n".join(result.chunk.text for result in citations)
        answer = self.llm.generate(
            [
                LLMMessage(
                    role="system",
                    content="Answer using only the provided FoldMind document context.",
                ),
                LLMMessage(role="user", content=f"Context:\n{context}\n\nQuestion:\n{query.text}"),
            ]
        )
        return GeneratedTextResult(text=answer, citations=citations)
