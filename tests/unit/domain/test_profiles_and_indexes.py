from __future__ import annotations

import unittest

from foldmind_ai_core.domain.common import Confidence
from foldmind_ai_core.domain.profiling.models import DocumentProfile
from foldmind_ai_core.domain.profiling.concepts import profile_concepts_from_labels
from foldmind_ai_core.domain.reference.documents import (
    DocumentVectorProjection,
    SourceDocument,
)
from foldmind_ai_core.domain.reference.folders import FolderVectorProjection, SourceFolder
from foldmind_ai_core.domain.retrieval.results import RetrievedFolder


class ProfileIndexBoundaryTests(unittest.TestCase):
    def test_document_vector_projection_uses_profile_without_overwriting_document(self) -> None:
        source = SourceDocument(
            tenant="tenant-1",
            document_type="document",
            document_id="doc-1",
            source_version="v1",
            title="MVP memo",
            body="Original body",
            folder_ids=("folder-1",),
            tag_ids=("memo",),
        )
        profile = DocumentProfile(
            tenant="tenant-1",
            document_type="document",
            document_id="doc-1",
            source_version="v1",
            title=source.title,
            summary="Startup MVP validation summary",
            profile_version="profile-v1",
            profile_schema_version="1",
            concepts=profile_concepts_from_labels(
                tenant="tenant-1",
                labels=("startup", "market validation", "MVP", "customer interview"),
                confidence=Confidence(0.82),
            ),
            profile_confidence=0.82,
        )

        projection = DocumentVectorProjection.from_profile(
            profile,
            embedding_model="test-embedding",
            embedding_version="test-v1",
            index_schema_version="schema-v1",
        )

        self.assertEqual(source.title, "MVP memo")
        self.assertEqual(source.body, "Original body")
        self.assertEqual(source.folder_ids, ("folder-1",))
        self.assertEqual(source.tag_ids, ("memo",))
        self.assertEqual(projection.profile_version, "profile-v1")
        self.assertEqual(
            projection.concept_ids,
            tuple(concept.concept_id for concept in profile.concepts),
        )
        self.assertIn("MVP memo", projection.embedding_input)
        self.assertIn("Startup MVP validation summary", projection.embedding_input)
        self.assertIn("customer interview", projection.embedding_input)

    def test_folder_vector_projection_uses_source_folder_metadata(self) -> None:
        source = SourceFolder(
            tenant="tenant-1",
            folder_id="folder-1",
            source_version="folder-v1",
            name="Founding",
            path="/Company/Founding",
            description="Original description",
            parent_folder_id="root",
        )

        projection = FolderVectorProjection.from_source(
            source,
            embedding_model="test-embedding",
            embedding_version="test-v1",
            index_schema_version="schema-v1",
        )

        self.assertEqual(source.name, "Founding")
        self.assertEqual(source.description, "Original description")
        self.assertEqual(source.parent_folder_id, "root")
        self.assertEqual(projection.source_version, "folder-v1")
        self.assertIn("Founding", projection.embedding_input)
        self.assertIn("/Company/Founding", projection.embedding_input)
        self.assertIn("Original description", projection.embedding_input)
        self.assertTrue(projection.embedding_input_hash)

    def test_retrieved_folder_is_plain_reference(self) -> None:
        folder = RetrievedFolder(
            tenant="tenant-1",
            folder_id="folder-1",
            source_version="folder-v1",
        )
        blank_version = RetrievedFolder(
            tenant="tenant-1",
            folder_id="folder-1",
            source_version="",
        )

        self.assertEqual(folder.folder_id, "folder-1")
        self.assertEqual(blank_version.source_version, "")


if __name__ == "__main__":
    unittest.main()
