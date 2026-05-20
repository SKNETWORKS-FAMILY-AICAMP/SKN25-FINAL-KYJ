from __future__ import annotations

import unittest

from foldmind_ai_core.core.application.models.projection_inputs import (
    ProjectionDocument,
    ProjectionDocumentFolderRelationSnapshot,
    ProjectionDocumentSignal,
    ProjectionFolderSignal,
    ProjectionDocumentProfile,
    ProjectionSignalEvidence,
)
from foldmind_ai_core.core.application.projections.factories import (
    document_folder_relation_projection_from_snapshot,
    document_relationship_projection_from_source_document,
    document_signal_graph_projection_from_profile,
    document_vector_projection_from_profile,
    folder_relationship_projection_from_source_folder,
    folder_signal_vector_projection_from_signal,
    folder_vector_projection_from_source,
    signal_vector_projection_from_signal,
)
from foldmind_ai_core.core.domain.models.reference.folders import SourceFolder


class ProjectionFactoryTests(unittest.TestCase):
    def test_document_relationship_projection_uses_source_document_identity(self) -> None:
        document = ProjectionDocument(
            tenant="tenant-1",
            document_type="document",
            document_id="doc-1",
            source_version="v1",
            content_digest="content-digest-1",
            content_size_bytes=42,
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
            title="MVP memo",
        )
        projection = document_relationship_projection_from_source_document(document)

        self.assertEqual(projection.document_id, "doc-1")
        self.assertEqual(projection.source_version, "v1")
        self.assertEqual(projection.created_at, document.created_at)
        self.assertEqual(projection.updated_at, document.updated_at)

    def test_document_folder_relation_projection_uses_relation_snapshot(self) -> None:
        relation_snapshot = ProjectionDocumentFolderRelationSnapshot(
            tenant="tenant-1",
            document_id="doc-1",
            source_version="v1",
            folder_ids=("folder-1",),
        )

        projection = document_folder_relation_projection_from_snapshot(
            relation_snapshot
        )

        self.assertEqual(projection.tenant, "tenant-1")
        self.assertEqual(projection.document_id, "doc-1")
        self.assertEqual(projection.source_version, "v1")
        self.assertEqual(projection.folder_ids, ("folder-1",))

    def test_document_signal_graph_projection_uses_profile_manifest_and_signals(self) -> None:
        profile = _profile()
        signals = (_summary_signal(), _concept_signal())

        projection = document_signal_graph_projection_from_profile(profile, signals)

        self.assertEqual(projection.document_id, "doc-1")
        self.assertEqual(projection.index_input_digest, "index-input-v1")
        self.assertEqual(projection.signals[0].signal_type, "summary")
        self.assertEqual(projection.signals[1].signal_key, "startup")
        self.assertEqual(projection.signals[0].generation_model, "test-model")

    def test_document_vector_projection_uses_document_level_signals(self) -> None:
        profile = _profile()
        signals = (
            _summary_signal(),
            _concept_signal(),
            ProjectionDocumentSignal(
                signal_id="signal-other-document",
                tenant="tenant-1",
                document_type="document",
                document_id="doc-2",
                source_version="v1",
                content_digest="content-digest-1",
                index_input_digest="index-input-v1",
                signal_type="concept",
                signal_key="other-document",
                text="Other document concept",
            ),
        )

        projection = document_vector_projection_from_profile(
            profile,
            signals,
            embedding_model="test-embedding",
            embedding_version="test-v1",
            index_schema_version="schema-v1",
        )

        self.assertIn("MVP memo", projection.embedding_input)
        self.assertIn("Startup MVP validation summary", projection.embedding_input)
        self.assertIn("customer interview", projection.embedding_input)
        self.assertNotIn("Other document concept", projection.embedding_input)

    def test_signal_vector_projection_uses_signal_text_and_evidence(self) -> None:
        signal = _concept_signal()

        projection = signal_vector_projection_from_signal(
            signal,
            embedding_model="test-embedding",
            embedding_version="test-v1",
            index_schema_version="schema-v1",
        )

        self.assertEqual(projection.signal_id, "signal-concept")
        self.assertEqual(projection.document_type, "document")
        self.assertEqual(projection.embedding_input, "customer interview")
        self.assertEqual(projection.evidence[0].chunk_id, "chunk-1")

    def test_folder_signal_vector_projection_uses_signal_text_and_folder_metadata(
        self,
    ) -> None:
        signal = ProjectionFolderSignal(
            signal_id="folder-signal-1",
            tenant="tenant-1",
            folder_id="folder-1",
            source_version="folder-v1",
            signal_type="responsibility",
            signal_key="responsibility",
            text="Folder responsibility matches member documents.",
            index_input_digest="folder-signal-input-v1",
            attributes={"responsibility_score": 0.82},
            related_document_id="doc-2",
            evidence=({"reason": "outlier"},),
            confidence=0.9,
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
        self.assertTrue(projection.index_input_digest)

    def test_folder_relationship_projection_uses_only_source_hierarchy(self) -> None:
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
        )

        projection = folder_relationship_projection_from_source_folder(folder)

        self.assertEqual(projection.folder_id, "folder-1")
        self.assertEqual(projection.name, "Founding")
        self.assertEqual(projection.path, "/Company/Founding")
        self.assertEqual(projection.source_version, "folder-v1")
        self.assertEqual(projection.created_at, folder.created_at)
        self.assertEqual(projection.updated_at, folder.updated_at)
        self.assertEqual(projection.parent_folder_id, "root")

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
        )

        projection = folder_vector_projection_from_source(
            folder,
            embedding_model="test-embedding",
            embedding_version="test-v1",
            index_schema_version="schema-v1",
        )

        self.assertEqual(projection.folder_id, "folder-1")
        self.assertEqual(projection.source_version, "folder-v1")
        self.assertIn("Founding", projection.embedding_input)
        self.assertIn("/Company/Founding", projection.embedding_input)
        self.assertIn("Founder resources", projection.embedding_input)
        self.assertNotIn("Folder holds founder resources.", projection.embedding_input)
        self.assertNotIn("A legal memo is an outlier.", projection.embedding_input)


def _profile() -> ProjectionDocumentProfile:
    return ProjectionDocumentProfile(
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        source_version="v1",
        content_digest="content-digest-1",
        index_input_digest="index-input-v1",
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        title="MVP memo",
    )


def _summary_signal() -> ProjectionDocumentSignal:
    return ProjectionDocumentSignal(
        signal_id="signal-summary",
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        source_version="v1",
        content_digest="content-digest-1",
        index_input_digest="index-input-v1",
        signal_type="summary",
        signal_key="document-summary",
        text="Startup MVP validation summary",
        evidence=(ProjectionSignalEvidence(chunk_id="chunk-1", quote="summary quote"),),
        confidence=0.82,
        generation_model="test-model",
    )


def _concept_signal() -> ProjectionDocumentSignal:
    return ProjectionDocumentSignal(
        signal_id="signal-concept",
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        source_version="v1",
        content_digest="content-digest-1",
        index_input_digest="index-input-v1",
        signal_type="concept",
        signal_key="startup",
        text="customer interview",
        evidence=(ProjectionSignalEvidence(chunk_id="chunk-1", quote="customer quote"),),
        confidence=0.9,
        generation_model="test-model",
    )


if __name__ == "__main__":
    unittest.main()
