from __future__ import annotations

import json
import unittest

from foldmind_ai_core.core.application.services.retrieved_context import (
    format_untrusted_context,
)
from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.retrieval.results import RetrievalResult
from foldmind_ai_core.shared.validation import InvalidInputError


class RetrievedContextTests(unittest.TestCase):
    def test_context_formatter_rejects_malformed_limits(self) -> None:
        result = _retrieval_result(0.7)

        with self.assertRaises(InvalidInputError):
            format_untrusted_context([result], max_context_chars=True)
        with self.assertRaises(InvalidInputError):
            format_untrusted_context([result], max_items=0)
        with self.assertRaises(InvalidInputError):
            format_untrusted_context([result], max_chunk_chars=-1)

    def test_context_formatter_never_emits_non_standard_json_numbers(self) -> None:
        context = format_untrusted_context([_retrieval_result(float("nan"))])

        payload = json.loads(context)

        self.assertIsNone(payload["items"][0]["score"])
        self.assertNotIn("NaN", context)


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


if __name__ == "__main__":
    unittest.main()
