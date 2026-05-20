from __future__ import annotations

import unittest

from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.retrieval.results import (
    FolderRetrievalResult,
    RelatedRetrievalItem,
    RelatedRetrievalResult,
    RetrievalResult,
    RetrievedFolder,
)


def _retrieval_result(score: float) -> RetrievalResult:
    text = "retrieved evidence"
    return RetrievalResult(
        chunk=DocumentChunk(
            tenant="tenant-1",
            document_type="document",
            document_id="doc-1",
            source_version="v1",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
            chunk_id="doc-1:chunk:0",
            chunk_index=0,
            chunking_version="chunking-test-v1",
            text=text,
            text_hash="hash-1",
            start_offset=0,
            end_offset=len(text),
            embedding_model="test-embedding",
            embedding_version="test-v1",
            index_schema_version="schema-v1",
        ),
        score=score,
    )


class RetrievalResultTests(unittest.TestCase):
    def test_related_retrieval_confidence_uses_highest_item_score(self) -> None:
        result = RelatedRetrievalResult(
            items=[
                RelatedRetrievalItem(target=_retrieval_result(0.2)),
                RelatedRetrievalItem(
                    target=FolderRetrievalResult(
                        folder=RetrievedFolder(
                            tenant="tenant-1",
                            folder_id="folder-1",
                            source_version="v1",
                            created_at="2026-05-01T10:00:00+09:00",
                            updated_at="2026-05-02T11:00:00+09:00",
                        ),
                        score=0.9,
                    )
                ),
            ]
        )

        self.assertEqual(result.confidence, 0.9)


if __name__ == "__main__":
    unittest.main()
