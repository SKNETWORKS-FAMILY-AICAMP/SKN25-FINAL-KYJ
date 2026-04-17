from __future__ import annotations

from dataclasses import dataclass, field

from ai_core.schemas.retrieval import RetrievalResult


@dataclass(slots=True)
class GeneratedTextResult:
    text: str
    citations: list[RetrievalResult] = field(default_factory=list)


@dataclass(slots=True)
class DraftResult:
    draft: str
    citations: list[RetrievalResult] = field(default_factory=list)
