from __future__ import annotations

import unittest

from foldmind_ai_core.application.services.outbox_events import (
    document_indexed_event,
)
from foldmind_ai_core.adapters.inbound.messaging.message_codec import (
    document_indexed_event_from_outbox,
)
from foldmind_ai_core.domain.indexing.projection_events import (
    DocumentIndexedProjectionEvent,
)
from foldmind_ai_core.domain.indexing.chunks import DocumentChunk
from foldmind_ai_core.domain.profiling.concepts import profile_concepts_from_labels
from foldmind_ai_core.domain.profiling.models import DocumentProfile
from foldmind_ai_core.domain.reference.documents import SourceDocument


class OutboxEventCodecTests(unittest.TestCase):
    def test_document_event_carries_projection_input_snapshot(self) -> None:
        source = SourceDocument(
            tenant="tenant-1",
            document_type="document",
            document_id="doc-1",
            source_version="v1",
            title="MVP memo",
            body="Original body",
            folder_ids=("folder-1",),
            tag_ids=("tag-1",),
            metadata={"source": "app"},
        )
        chunk = DocumentChunk(
            tenant=source.tenant,
            document_type=source.document_type,
            document_id=source.document_id,
            source_version=source.source_version,
            chunk_id="chunk-1",
            chunk_index=0,
            chunking_version="chunking-test-v1",
            text="chunk text",
            text_hash="hash-1",
            start_offset=0,
            end_offset=10,
            embedding_model="embedding",
            embedding_version="v1",
            index_schema_version="schema-v1",
        )
        profile = DocumentProfile(
            tenant=source.tenant,
            document_type=source.document_type,
            document_id=source.document_id,
            source_version=source.source_version,
            title=source.title,
            summary="Summary",
            profile_version="profile-v1",
            profile_schema_version="1",
            concepts=profile_concepts_from_labels(
                tenant=source.tenant,
                labels=("startup",),
            ),
        )

        event = document_indexed_event(
            document=source,
            chunks=(chunk,),
            profile=profile,
        )

        self.assertEqual(f"{event.aggregate_type}:{event.aggregate_id}", "DOCUMENT:doc-1")
        self.assertEqual(event.event_type, "DOCUMENT_INDEXED")
        decoded = document_indexed_event_from_outbox(event)
        self.assertIsInstance(decoded, DocumentIndexedProjectionEvent)
        assert isinstance(decoded, DocumentIndexedProjectionEvent)
        self.assertEqual(decoded.document.folder_ids, ("folder-1",))
        self.assertEqual(decoded.profile, profile)
        self.assertEqual(event.payload["chunks"][0]["text"], "chunk text")


if __name__ == "__main__":
    unittest.main()
