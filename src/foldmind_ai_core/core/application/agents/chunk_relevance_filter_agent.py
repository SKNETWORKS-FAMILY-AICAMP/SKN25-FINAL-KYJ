from __future__ import annotations

import json
import math
from dataclasses import dataclass

from foldmind_ai_core.core.application.agents.json_output import parse_json_object_output
from foldmind_ai_core.core.application.errors import InvalidAgentOutputError
from foldmind_ai_core.core.application.models.llm import LLMMessage
from foldmind_ai_core.core.application.ports.outbound.llm import LLMProvider
from foldmind_ai_core.core.application.ports.outbound.prompt_store import PromptStore
from foldmind_ai_core.core.application.queries.retrieval import RetrievalQuery
from foldmind_ai_core.core.application.services.prompts import (
    PROMPT_CHUNK_RELEVANCE_FILTERING,
)
from foldmind_ai_core.core.domain.models.retrieval.results import RetrievalResult
from foldmind_ai_core.shared.types import JsonObject
from foldmind_ai_core.shared.validation import InvalidInputError


@dataclass(slots=True)
class ChunkRelevanceFilterAgent:
    llm: LLMProvider
    prompt_store: PromptStore
    min_confidence: float = 0.5

    def __post_init__(self) -> None:
        if (
            isinstance(self.min_confidence, bool)
            or not isinstance(self.min_confidence, int | float)
        ):
            raise InvalidInputError("min_confidence must be numeric.")
        min_confidence = float(self.min_confidence)
        if not math.isfinite(min_confidence) or not 0.0 <= min_confidence <= 1.0:
            raise InvalidInputError("min_confidence must be between 0 and 1.")
        self.min_confidence = min_confidence

    def filter(
        self,
        *,
        query: RetrievalQuery,
        results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        if not results:
            return []
        raw = self._generate(query, results)
        try:
            parsed = parse_json_object_output(raw)
        except (json.JSONDecodeError, ValueError):
            raise InvalidAgentOutputError(
                "Chunk relevance filter response must be a JSON object."
            ) from None
        relevant_ids = self._relevant_chunk_ids(parsed)
        return [result for result in results if result.chunk.chunk_id in relevant_ids]

    def _generate(self, query: RetrievalQuery, results: list[RetrievalResult]) -> str:
        system = self.prompt_store.get(PROMPT_CHUNK_RELEVANCE_FILTERING)
        return self.llm.generate(
            [
                LLMMessage(role="system", content=system),
                LLMMessage(
                    role="user",
                    content=json.dumps(
                        {
                            "query": query.text,
                            "chunks": [
                                {
                                    "chunk_id": result.chunk.chunk_id,
                                    "text": result.chunk.text,
                                    "score": result.score,
                                    "document_type": result.chunk.document_type,
                                    "document_id": result.chunk.document_id,
                                }
                                for result in results
                            ],
                        },
                        ensure_ascii=False,
                    ),
                ),
            ]
        )

    def _relevant_chunk_ids(self, payload: JsonObject) -> set[str]:
        results = payload.get("results")
        if not isinstance(results, list):
            raise InvalidAgentOutputError(
                "Chunk relevance filter response must include results."
            )
        relevant: set[str] = set()
        for item in results:
            if not isinstance(item, dict):
                raise InvalidAgentOutputError(
                    "Chunk relevance filter results must be objects."
                )
            chunk_id = self._chunk_id(item)
            is_relevant = self._relevant(item)
            confidence = self._confidence(item)
            if is_relevant and confidence >= self.min_confidence:
                relevant.add(chunk_id)
        return relevant

    def _chunk_id(self, item: JsonObject) -> str:
        value = item.get("chunk_id")
        if not isinstance(value, str) or not value.strip():
            raise InvalidAgentOutputError(
                "Chunk relevance filter results must include chunk_id."
            )
        return value.strip()

    def _relevant(self, item: JsonObject) -> bool:
        value = item.get("relevant")
        if not isinstance(value, bool):
            raise InvalidAgentOutputError(
                "Chunk relevance filter results must include relevant as a boolean."
            )
        return value

    def _confidence(self, item: JsonObject) -> float:
        value = item.get("confidence")
        if value is None:
            raise InvalidAgentOutputError(
                "Chunk relevance filter results must include confidence."
            )
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise InvalidAgentOutputError(
                "Chunk relevance filter confidence must be numeric."
            )
        confidence = float(value)
        if not math.isfinite(confidence) or confidence < 0.0 or confidence > 1.0:
            raise InvalidAgentOutputError(
                "Chunk relevance filter confidence must be between 0 and 1."
            )
        return confidence
