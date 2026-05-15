from __future__ import annotations

import unittest

from foldmind_ai_core.domain.common import Confidence
from foldmind_ai_core.domain.knowledge_graph.models import DocumentConceptProjection
from foldmind_ai_core.domain.profiling.models import DocumentProfile, ProfileConcept


class OntologyGraphDomainTests(unittest.TestCase):
    def test_confidence_is_plain_value_object(self) -> None:
        confidence = Confidence(1.1)

        self.assertEqual(confidence.value, 1.1)

    def test_document_concept_projection_is_created_from_profile(self) -> None:
        profile = DocumentProfile(
            tenant="tenant-1",
            document_type="document",
            document_id="doc-1",
            source_version="v1",
            title="Startup memo",
            summary="Startup memo summary",
            profile_version="profile-v1",
            profile_schema_version="profile-schema-v1",
            concepts=(
                ProfileConcept(
                    concept_id="concept-1",
                    concept_key="startup",
                    label="Startup",
                    confidence=0.9,
                ),
            ),
            profile_confidence=0.8,
            model="test-model",
            prompt_version="test-prompt",
        )

        projection = DocumentConceptProjection.from_profile(profile)

        self.assertEqual(projection.document_id, "doc-1")
        self.assertEqual(projection.profile_version, "profile-v1")
        self.assertEqual(projection.concepts[0].concept_id, "concept-1")
        self.assertEqual(projection.metadata["profile_schema_version"], "profile-schema-v1")


if __name__ == "__main__":
    unittest.main()
