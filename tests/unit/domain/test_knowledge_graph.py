from __future__ import annotations

import hashlib
import unittest

from foldmind_ai_core.core.domain.models.confidence import Confidence
from foldmind_ai_core.core.domain.models.document_sources import SourceDocument
from foldmind_ai_core.core.domain.models.folder_index_state import (
    FolderIndexState,
    FolderSignalRefreshStatus,
)
from foldmind_ai_core.shared.validation import InvalidInputError


class ConfidenceDomainTests(unittest.TestCase):
    def test_confidence_rejects_out_of_range_values(self) -> None:
        confidence = Confidence(1.0)

        self.assertEqual(confidence.value, 1.0)
        with self.assertRaises(InvalidInputError):
            Confidence(1.1)
        with self.assertRaises(InvalidInputError):
            Confidence(float("nan"))


class SourceDocumentDomainTests(unittest.TestCase):
    def test_source_document_exposes_content_digest_and_size(self) -> None:
        document = SourceDocument(
            tenant="tenant-1",
            document_id="document-1",
            document_type="note",
            title="Title",
            body="Hello",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            metadata={"kind": "test"},
            source_version="3",
        )

        self.assertEqual(
            hashlib.sha256(document.full_text.encode("utf-8")).hexdigest(),
            document.content_digest,
        )
        self.assertEqual(
            len(document.full_text.encode("utf-8")),
            document.content_size_bytes,
        )


class FolderIndexStateDomainTests(unittest.TestCase):
    def test_folder_signal_refresh_status_matches_storage_values(self) -> None:
        self.assertEqual(
            ["empty", "pending", "ready", "failed"],
            [status.value for status in FolderSignalRefreshStatus],
        )
        self.assertEqual(
            FolderSignalRefreshStatus.EMPTY,
            FolderIndexState(
                folder_id="folder-1",
                folder_index_input_digest="folder-index-digest",
                folder_signal_input_digest="folder-signal-digest",
            ).folder_signal_refresh_status,
        )


if __name__ == "__main__":
    unittest.main()
