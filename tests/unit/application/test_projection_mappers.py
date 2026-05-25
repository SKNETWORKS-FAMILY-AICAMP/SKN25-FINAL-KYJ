from __future__ import annotations

import unittest
from dataclasses import replace

from foldmind_ai_core.core.application.mappers.projection import (
    document_vector_projection_from_index_record,
    folder_signal_vector_projection_from_signal,
    folder_vector_projection_from_source,
    signal_vector_projection_from_signal,
)
from foldmind_ai_core.core.domain.models.document_index_state import DocumentIndexState
from foldmind_ai_core.core.domain.models.document_folder_relations import (
    SourceDocumentFolderRelationSnapshot,
)
from foldmind_ai_core.core.domain.models.document_signals import (
    DocumentSignal,
    DocumentSignalEvidence,
    DocumentSignalType,
)
from foldmind_ai_core.core.domain.models.document_sources import DocumentSourceState
from foldmind_ai_core.core.domain.models.folder_signals import (
    FolderSignal,
    FolderSignalType,
)
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder
from foldmind_ai_core.core.domain.services.folder_projection_digest_service import (
    FolderProjectionDigestService,
)


class ProjectionMapperTests(unittest.TestCase):
    def test_document_folder_relation_projection_uses_domain_snapshot(self) -> None:
        relation_snapshot = SourceDocumentFolderRelationSnapshot(
            tenant="tenant-1",
            document_id="doc-1",
            source_version="v1",
            folder_ids=("folder-1",),
        )

        self.assertEqual(relation_snapshot.tenant, "tenant-1")
        self.assertEqual(relation_snapshot.document_id, "doc-1")
        self.assertEqual(relation_snapshot.source_version, "v1")
        self.assertEqual(relation_snapshot.folder_ids, ("folder-1",))

    def test_document_vector_projection_uses_document_level_signals(self) -> None:
        document = _document()
        index_record = _document_index_record()
        signals = (
            _summary_signal(),
            _concept_signal(),
            DocumentSignal(
                signal_id="signal-other-document",
                tenant="tenant-1",
                document_type="document",
                document_id="doc-2",
                source_version="v1",
                document_signal_input_digest="index-input-v1",
                signal_type=DocumentSignalType.CONCEPT,
                signal_key="other-document",
                text="Other document concept",
                extractor_name="test-extractor",
                extractor_version="test-extractor-v1",
            ),
        )

        projection = document_vector_projection_from_index_record(
            document,
            index_record,
            signals,
            embedding_model="test-embedding",
            embedding_version="test-v1",
            index_schema_version="schema-v1",
        )

        self.assertIn("MVP memo", projection.embedding_input)
        self.assertEqual(projection.title, "MVP memo")
        self.assertEqual(projection.metadata, {"scope": "research"})
        self.assertIn("Startup MVP validation summary", projection.embedding_input)
        self.assertIn("customer interview", projection.embedding_input)
        self.assertNotIn("Other document concept", projection.embedding_input)

    def test_signal_vector_projection_uses_signal_text_and_evidence(self) -> None:
        signal = _concept_signal()

        projection = signal_vector_projection_from_signal(
            signal,
            content_digest="content-digest-1",
            embedding_model="test-embedding",
            embedding_version="test-v1",
            index_schema_version="schema-v1",
        )

        self.assertEqual(projection.signal_id, "signal-concept")
        self.assertEqual(projection.document_type, "document")
        self.assertEqual(projection.embedding_input, "customer interview")
        self.assertEqual(projection.evidence[0].chunk_id, "chunk-1")
        self.assertEqual(projection.extractor_name, "test-extractor")
        self.assertEqual(projection.extractor_version, "test-extractor-v1")
        self.assertEqual(projection.generation_model, "test-model")

    def test_folder_signal_vector_projection_uses_signal_text_and_folder_metadata(
        self,
    ) -> None:
        signal = FolderSignal(
            signal_id="folder-signal-1",
            tenant="tenant-1",
            folder_id="folder-1",
            source_version="folder-v1",
            signal_type=FolderSignalType.RESPONSIBILITY,
            signal_key="responsibility",
            text="Folder responsibility matches member documents.",
            folder_signal_input_digest="folder-signal-input-v1",
            attributes={"responsibility_score": 0.82},
            related_document_id="doc-2",
            evidence=({"reason": "outlier"},),
            confidence=0.9,
            extractor_name="folder-extractor",
            extractor_version="folder-extractor-v1",
            generation_model="folder-model",
        )

        projection = folder_signal_vector_projection_from_signal(
            signal,
            embedding_model="test-embedding",
            embedding_version="test-v1",
            index_schema_version="schema-v1",
        )

        self.assertEqual(projection.signal_id, "folder-signal-1")
        self.assertEqual(projection.folder_id, "folder-1")
        self.assertEqual(
            projection.embedding_input,
            "Folder responsibility matches member documents.",
        )
        self.assertEqual(projection.attributes["responsibility_score"], 0.82)
        self.assertEqual(projection.related_document_id, "doc-2")
        self.assertEqual(projection.evidence[0]["reason"], "outlier")
        self.assertEqual(projection.extractor_name, "folder-extractor")
        self.assertEqual(projection.extractor_version, "folder-extractor-v1")
        self.assertEqual(projection.generation_model, "folder-model")
        self.assertEqual(
            projection.source_input_digest,
            "folder-signal-input-v1",
        )
        self.assertTrue(projection.vector_input_digest)

    def test_folder_vector_projection_uses_folder_metadata(self) -> None:
        folder = SourceFolder(
            tenant="tenant-1",
            folder_id="folder-1",
            source_version="folder-v1",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
            name="Founding",
            path="/Company/Founding",
            description="Founder resources",
            parent_folder_id="root",
            metadata={"scope": "research"},
        )

        projection = folder_vector_projection_from_source(
            folder,
            embedding_model="test-embedding",
            embedding_version="test-v1",
            index_schema_version="schema-v1",
        )

        self.assertEqual(projection.folder_id, "folder-1")
        self.assertEqual(projection.source_version, "folder-v1")
        self.assertEqual(projection.name, "Founding")
        self.assertEqual(projection.path, "/Company/Founding")
        self.assertEqual(projection.parent_folder_id, "root")
        self.assertEqual(projection.description, "Founder resources")
        self.assertEqual(projection.metadata, {"scope": "research"})
        self.assertIn("Founding", projection.embedding_input)
        self.assertIn("/Company/Founding", projection.embedding_input)
        self.assertIn("Founder resources", projection.embedding_input)
        self.assertNotIn("Folder holds founder resources.", projection.embedding_input)
        self.assertNotIn("A legal memo is an outlier.", projection.embedding_input)

    def test_folder_index_digest_tracks_hierarchy_and_metadata_inputs(self) -> None:
        folder = SourceFolder(
            tenant="tenant-1",
            folder_id="folder-1",
            source_version="folder-v1",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
            name="Founding",
            path=None,
            description="Founder resources",
            parent_folder_id="root",
            metadata={"scope": "research"},
        )

        digest_service = FolderProjectionDigestService()
        digest = digest_service.folder_index_input_digest(
            folder_id=folder.folder_id,
            folder=folder,
        )
        vector = folder_vector_projection_from_source(
            folder,
            embedding_model="test-embedding",
            embedding_version="test-v1",
            index_schema_version="schema-v1",
        )
        parent_changed = digest_service.folder_index_input_digest(
            folder_id=folder.folder_id,
            folder=replace(folder, parent_folder_id="archive"),
        )
        metadata_changed = digest_service.folder_index_input_digest(
            folder_id=folder.folder_id,
            folder=replace(folder, metadata={"scope": "operations"}),
        )
        version_changed = digest_service.folder_index_input_digest(
            folder_id=folder.folder_id,
            folder=replace(folder, source_version="folder-v2"),
        )

        self.assertEqual(digest, vector.source_input_digest)
        self.assertNotEqual(digest, parent_changed)
        self.assertNotEqual(digest, metadata_changed)
        self.assertEqual(digest, version_changed)

    def test_folder_signal_digest_is_independent_from_member_input_order(self) -> None:
        digest_service = FolderProjectionDigestService()
        doc_a = replace(
            _document(),
            document_id="doc-a",
            content_digest="content-a",
        )
        doc_b = replace(
            _document(),
            document_id="doc-b",
            content_digest="content-b",
        )
        index_a = DocumentIndexState(
            document_id="doc-a",
            document_index_input_digest="index-a",
            document_signal_input_digest="signal-a",
        )
        index_b = DocumentIndexState(
            document_id="doc-b",
            document_index_input_digest="index-b",
            document_signal_input_digest="signal-b",
        )

        digest = digest_service.folder_signal_input_digest(
            document_sources=(doc_b, doc_a),
            document_index_states=(index_b, index_a),
            folder_index_input_digest="folder-index",
            signal_generation_version="1",
        )
        reordered_digest = digest_service.folder_signal_input_digest(
            document_sources=(doc_a, doc_b),
            document_index_states=(index_a, index_b),
            folder_index_input_digest="folder-index",
            signal_generation_version="1",
        )

        self.assertEqual(digest, reordered_digest)


def _document() -> DocumentSourceState:
    return DocumentSourceState(
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        source_version="v1",
        content_digest="content-digest-1",
        content_size_bytes=42,
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        title="MVP memo",
        metadata={"scope": "research"},
    )


def _document_index_record() -> DocumentIndexState:
    return DocumentIndexState(
        document_id="doc-1",
        document_index_input_digest="index-input-v1",
        document_signal_input_digest="document-signal-input-v1",
    )


def _summary_signal() -> DocumentSignal:
    return DocumentSignal(
        signal_id="signal-summary",
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        source_version="v1",
        document_signal_input_digest="document-signal-input-v1",
        signal_type=DocumentSignalType.SUMMARY,
        signal_key="document-summary",
        text="Startup MVP validation summary",
        evidence=(DocumentSignalEvidence(chunk_id="chunk-1", quote="summary quote"),),
        confidence=0.82,
        extractor_name="test-extractor",
        extractor_version="test-extractor-v1",
        generation_model="test-model",
    )


def _concept_signal() -> DocumentSignal:
    return DocumentSignal(
        signal_id="signal-concept",
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        source_version="v1",
        document_signal_input_digest="document-signal-input-v1",
        signal_type=DocumentSignalType.CONCEPT,
        signal_key="startup",
        text="customer interview",
        evidence=(DocumentSignalEvidence(chunk_id="chunk-1", quote="customer quote"),),
        confidence=0.9,
        extractor_name="test-extractor",
        extractor_version="test-extractor-v1",
        generation_model="test-model",
    )


if __name__ == "__main__":
    unittest.main()
