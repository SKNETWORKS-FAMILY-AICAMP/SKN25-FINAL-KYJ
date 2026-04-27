from __future__ import annotations

from dataclasses import dataclass

from ai_core.domain.tasks import AIQuery, RequestContext


@dataclass(slots=True)
class QueryInterpreterAgent:
    def interpret(self, *, text: str, context: RequestContext) -> AIQuery:
        return AIQuery(text=text, request_context=context)
