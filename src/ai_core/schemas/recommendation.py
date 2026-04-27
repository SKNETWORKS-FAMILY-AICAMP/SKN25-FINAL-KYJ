"""Compatibility re-exports for recommendation results."""

from ai_core.domain.tasks import (
    DocumentRecommendation,
    DocumentRecommendationResult,
    FolderRecommendation,
    FolderRecommendationResult,
    RelatedRecommendationItem,
    RelatedRecommendationResult,
)

__all__ = [
    "DocumentRecommendation",
    "DocumentRecommendationResult",
    "FolderRecommendation",
    "FolderRecommendationResult",
    "RelatedRecommendationItem",
    "RelatedRecommendationResult",
]
