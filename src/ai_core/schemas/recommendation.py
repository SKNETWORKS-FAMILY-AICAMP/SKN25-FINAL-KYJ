from __future__ import annotations

from dataclasses import dataclass, field

from ai_core.schemas.source_folder import SourceFolder


@dataclass(slots=True)
class FolderRecommendation:
    folder: SourceFolder
    reason: str
    score: float


@dataclass(slots=True)
class FolderRecommendationResult:
    primary: FolderRecommendation
    alternatives: list[FolderRecommendation] = field(default_factory=list)
