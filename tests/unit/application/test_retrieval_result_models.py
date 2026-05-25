from __future__ import annotations

import unittest

from foldmind_ai_core.core.application.models.retrieval import (
    FolderRetrievalResult,
    RelatedRetrievalResult,
    RetrievalResult,
)
from foldmind_ai_core.core.domain.models.document_chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder


def _retrieval_result(score: float) -> RetrievalResult:
    text = "retrieved evidence"
    return RetrievalResult(
        chunk=DocumentChunk(
            tenant="tenant-1",
            document_type="document",
            document_id="doc-1",
            source_version="v1",
            document_index_input_digest="index-input-v1",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
            chunk_id="doc-1:chunk:0",
            chunk_index=0,
            text=text,
            start_offset=0,
            end_offset=len(text),
        ),
        score=score,
    )


def _source_folder(
    folder_id: str,
    *,
    source_version: str = "folder-v1",
) -> SourceFolder:
    return SourceFolder(
        tenant="tenant-1",
        folder_id=folder_id,
        source_version=source_version,
        name=folder_id,
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
    )


class RetrievalResultTests(unittest.TestCase):
    def test_folder_retrieval_result_uses_source_folder(self) -> None:
        folder = _source_folder("folder-1")
        blank_version = _source_folder("folder-1", source_version="")

        self.assertEqual(folder.folder_id, "folder-1")
        self.assertEqual(blank_version.source_version, "")

    def test_related_retrieval_confidence_uses_highest_item_score(self) -> None:
        result = RelatedRetrievalResult(
            items=[
                _retrieval_result(0.2),
                FolderRetrievalResult(
                    folder=_source_folder("folder-1", source_version="v1"),
                    score=0.9,
                ),
            ]
        )

        self.assertEqual(result.confidence, 0.9)


if __name__ == "__main__":
    unittest.main()
