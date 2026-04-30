from __future__ import annotations

from dataclasses import dataclass

from ai_core.application.models.llm import LLMMessage
from ai_core.application.models.results import GeneratedTextResult
from ai_core.application.models.retrieval import RetrievalResult
from ai_core.application.ports.llm import LLM


@dataclass(slots=True)
class SummarizerAgent:
    llm: LLM

    def summarize(self, results: list[RetrievalResult]) -> GeneratedTextResult:
        context = "\n\n".join(result.chunk.text for result in results)
        text = self.llm.generate(
            [
                LLMMessage(role="system", content="Summarize the provided FoldMind context."),
                LLMMessage(role="user", content=context),
            ]
        )
        return GeneratedTextResult(text=text, citations=results)
