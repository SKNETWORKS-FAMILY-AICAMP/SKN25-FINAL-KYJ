from __future__ import annotations

import unittest

from foldmind_ai_core.domain.common import Confidence
from foldmind_ai_core.domain.knowledge_graph.models import (
    DocumentConceptProjection,
    DocumentRelationshipProjection,
    FolderRelationshipProjection,
)
from foldmind_ai_core.domain.profiling.concepts import profile_concepts_from_labels
from foldmind_ai_core.domain.profiling.models import DocumentProfile
from foldmind_ai_core.domain.reference.documents import SourceDocument
from foldmind_ai_core.domain.reference.folders import SourceFolder


class ProjectionFactoryTests(unittest.TestCase):
    def test_document_relationship_projection_uses_only_source_relationships(self) -> None:
        document = SourceDocument(
            tenant="tenant-1",
            document_type="document",
            document_id="doc-1",
            source_version="v1",
            title="MVP memo",
            body="Initial customer interviews narrowed the MVP.",
            folder_ids=("folder-1",),
            tag_ids=("memo",),
        )

        projection = DocumentRelationshipProjection.from_source_document(document)

        self.assertEqual(projection.document_id, "doc-1")
        self.assertEqual(projection.folder_ids, ("folder-1",))
        self.assertEqual(projection.tag_ids, ("memo",))
        self.assertEqual(projection.source_version, "v1")

    def test_document_concept_projection_uses_only_profile_concepts(self) -> None:
        concepts = profile_concepts_from_labels(
            tenant="tenant-1",
            labels=("startup", "market validation"),
            confidence=Confidence(0.8),
        )
        profile = DocumentProfile(
            tenant="tenant-1",
            document_type="document",
            document_id="doc-1",
            source_version="v1",
            title="MVP memo",
            summary="Startup market validation memo",
            profile_version="profile-v1",
            profile_schema_version="1",
            concepts=concepts,
            profile_confidence=0.8,
        )

        projection = DocumentConceptProjection.from_profile(profile)

        self.assertEqual(projection.document_id, "doc-1")
        self.assertEqual(projection.profile_version, "profile-v1")
        self.assertEqual(tuple(concept.label for concept in projection.concepts), (
            "startup",
            "market validation",
        ))

    def test_folder_relationship_projection_uses_only_source_hierarchy(self) -> None:
        folder = SourceFolder(
            tenant="tenant-1",
            folder_id="folder-1",
            source_version="folder-v1",
            name="Founding",
            path="/Company/Founding",
            description="Founder resources",
            parent_folder_id="root",
        )

        projection = FolderRelationshipProjection.from_source_folder(folder)

        self.assertEqual(projection.folder_id, "folder-1")
        self.assertEqual(projection.source_version, "folder-v1")
        self.assertEqual(projection.parent_folder_id, "root")


if __name__ == "__main__":
    unittest.main()
