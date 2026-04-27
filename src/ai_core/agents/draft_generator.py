from __future__ import annotations

from dataclasses import dataclass

from ai_core.application.ports.llm import LLM
from ai_core.domain.chunks import RetrievalResult
from ai_core.domain.tasks import DraftResult, LLMMessage


@dataclass(slots=True)
class DraftGeneratorAgent:
    llm: LLM

    def generate(self, *, instruction: str, citations: list[RetrievalResult]) -> DraftResult:
        context = "\n\n".join(result.chunk.text for result in citations)
        draft = self.llm.generate(
            [
                LLMMessage(role="system", content="Write a draft using the provided context."),
                LLMMessage(role="user", content=f"Context:\n{context}\n\nInstruction:\n{instruction}"),
            ]
        )
        return DraftResult(draft=draft, citations=citations)
