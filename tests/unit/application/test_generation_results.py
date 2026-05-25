from __future__ import annotations

import unittest

from foldmind_ai_core.core.application.models.generation import (
    DocumentRecommendation,
    DocumentSearchResult,
    FolderRecommendation,
    RelatedRecommendationResult,
)
from foldmind_ai_core.core.application.models.retrieval import RetrievedDocument


class GenerationResultTests(unittest.TestCase):
    def test_document_search_result_confidence_uses_highest_item_score(self) -> None:
        result = DocumentSearchResult(
            items=[
                DocumentRecommendation(
                    document=RetrievedDocument(
                        tenant="tenant-1",
                        document_type="document",
                        document_id="doc-1",
                        source_version="v1",
                    ),
                    reason="Document evidence.",
                    score=0.2,
                ),
                DocumentRecommendation(
                    document=RetrievedDocument(
                        tenant="tenant-1",
                        document_type="document",
                        document_id="doc-2",
                        source_version="v1",
                    ),
                    reason="Document evidence.",
                    score=0.9,
                ),
            ]
        )

        self.assertEqual(result.confidence, 0.9)

    def test_related_recommendation_confidence_uses_highest_item_score(self) -> None:
        result = RelatedRecommendationResult(
            items=[
                DocumentRecommendation(
                    document=RetrievedDocument(
                        tenant="tenant-1",
                        document_type="document",
                        document_id="doc-1",
                        source_version="v1",
                        created_at="2026-05-01T10:00:00+09:00",
                        updated_at="2026-05-02T11:00:00+09:00",
                    ),
                    reason="Document evidence.",
                    score=0.2,
                ),
                FolderRecommendation(
                    folder_id="folder-1",
                    reason="Folder evidence.",
                    score=0.9,
                ),
            ]
        )

        self.assertEqual(result.confidence, 0.9)


if __name__ == "__main__":
    unittest.main()
