from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from foldmind_ai_core.application.dto.llm import LLMMessage
from foldmind_ai_core.application.ports.outbound.llm import LLM
from foldmind_ai_core.application.ports.outbound.prompt_repository import PromptRepositoryPort
from foldmind_ai_core.application.services.prompts import PROMPT_CHUNK_RELEVANCE_VALIDATION
from foldmind_ai_core.domain.retrieval.queries import AIQuery
from foldmind_ai_core.domain.retrieval.results import RetrievalResult


@dataclass(slots=True)
class ChunkRelevanceValidatorAgent:
    llm: LLM
    prompt_repository: PromptRepositoryPort
    min_confidence: float = 0.5

    def filter(
        self,
        *,
        query: AIQuery,
        results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        if not results:
            return []
        raw = self._generate(query, results)
        parsed = self._parse_json(raw)
        if parsed is None:
            return results
        relevant_ids = self._relevant_chunk_ids(parsed)
        return [result for result in results if result.chunk.chunk_id in relevant_ids]

    def _generate(self, query: AIQuery, results: list[RetrievalResult]) -> str:
        try:
            system = self.prompt_repository.get(PROMPT_CHUNK_RELEVANCE_VALIDATION)
        except Exception:
            system = (
                "Validate which retrieved chunks are relevant to the user query. "
                "Return JSON with results containing chunk_id, relevant, confidence."
            )
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

    def _parse_json(self, raw: str) -> dict[str, Any] | list[Any] | None:
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return value if isinstance(value, dict | list) else None

    def _relevant_chunk_ids(self, payload: dict[str, Any] | list[Any]) -> set[str]:
        items: list[Any]
        if isinstance(payload, list):
            items = payload
        else:
            ids = payload.get("relevant_chunk_ids")
            if isinstance(ids, list):
                return {str(item) for item in ids if str(item).strip()}
            items = payload.get("results") if isinstance(payload.get("results"), list) else []
        relevant: set[str] = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            chunk_id = str(item.get("chunk_id") or "").strip()
            confidence = float(item.get("confidence") or 0.0)
            if chunk_id and item.get("relevant") is True and confidence >= self.min_confidence:
                relevant.add(chunk_id)
        return relevant
