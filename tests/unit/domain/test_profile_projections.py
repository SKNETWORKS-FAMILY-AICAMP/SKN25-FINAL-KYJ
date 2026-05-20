from __future__ import annotations

import unittest

from foldmind_ai_core.core.domain.models.profiling import (
    DocumentSignalType,
    FolderSignalType,
    SignalEvidence,
)
from foldmind_ai_core.core.domain.models.retrieval.results import RetrievedFolder
from foldmind_ai_core.core.domain.services.profiling import (
    DEFAULT_SIGNAL_DEFINITIONS,
    create_document_signal,
    create_folder_signal,
    document_signal_id,
    folder_signal_id,
)
from foldmind_ai_core.shared.validation import InvalidInputError


class ProfileDomainTests(unittest.TestCase):
    def test_signal_confidence_fields_reject_out_of_range_values(self) -> None:
        with self.assertRaises(InvalidInputError):
            create_document_signal(
                tenant="tenant-1",
                document_type="document",
                document_id="doc-1",
                source_version="v1",
                index_input_digest="index-input-v1",
                signal_type=DocumentSignalType.CONCEPT,
                text="Startup",
                attributes={"label": "Startup"},
                evidence=(SignalEvidence(chunk_id="chunk-1", quote="Startup"),),
                confidence=1.1,
                extractor_name="document_profiler",
                extractor_version="prompt-v1",
            )

    def test_document_signal_requires_supported_type_text_and_evidence(self) -> None:
        with self.assertRaises(InvalidInputError):
            create_document_signal(
                tenant="tenant-1",
                document_type="document",
                document_id="doc-1",
                source_version="v1",
                index_input_digest="index-input-v1",
                signal_type="unsupported",
                text="Unsupported",
                attributes={},
                evidence=(SignalEvidence(chunk_id="chunk-1", quote="quote"),),
                confidence=0.8,
                extractor_name="document_profiler",
                extractor_version="prompt-v1",
            )

        with self.assertRaises(InvalidInputError):
            create_document_signal(
                tenant="tenant-1",
                document_type="document",
                document_id="doc-1",
                source_version="v1",
                index_input_digest="index-input-v1",
                signal_type=DocumentSignalType.SUMMARY,
                text=" ",
                attributes={},
                evidence=(SignalEvidence(chunk_id="chunk-1", quote="quote"),),
                extractor_name="document_profiler",
                extractor_version="prompt-v1",
                confidence=0.8,
            )

        with self.assertRaises(InvalidInputError):
            create_document_signal(
                tenant="tenant-1",
                document_type="document",
                document_id="doc-1",
                source_version="v1",
                index_input_digest="index-input-v1",
                signal_type=DocumentSignalType.SUMMARY,
                text="Summary",
                attributes={},
                evidence=(),
                extractor_name="document_profiler",
                extractor_version="prompt-v1",
                confidence=0.8,
            )

    def test_signal_id_is_deterministic_for_same_index_input_digest_type_and_key(self) -> None:
        first = document_signal_id(
            tenant="tenant-1",
            document_id="doc-1",
            index_input_digest="index-input-v1",
            signal_type=DocumentSignalType.CONCEPT,
            signal_key="startup",
        )
        second = document_signal_id(
            tenant="tenant-1",
            document_id="doc-1",
            index_input_digest="index-input-v1",
            signal_type="concept",
            signal_key="startup",
        )

        self.assertEqual(first, second)

    def test_signal_id_ignores_document_type_identity(self) -> None:
        first_signal_id = document_signal_id(
            tenant="tenant-1",
            document_id="doc-1",
            index_input_digest="index-input-v1",
            signal_type=DocumentSignalType.CONCEPT,
            signal_key="startup",
        )
        second_signal_id = document_signal_id(
            tenant="tenant-1",
            document_id="doc-1",
            index_input_digest="index-input-v1",
            signal_type=DocumentSignalType.CONCEPT,
            signal_key="startup",
        )

        self.assertEqual(first_signal_id, second_signal_id)

    def test_summary_and_concept_are_registry_signals(self) -> None:
        self.assertIn(
            DocumentSignalType.SUMMARY,
            DEFAULT_SIGNAL_DEFINITIONS.allowed_types(),
        )
        self.assertIn(
            DocumentSignalType.CONCEPT,
            DEFAULT_SIGNAL_DEFINITIONS.allowed_types(),
        )

    def test_folder_signal_attributes_and_identity_are_supported(self) -> None:
        signal = create_folder_signal(
            tenant="tenant-1",
            folder_id="folder-1",
            source_version="v1",
            signal_type=FolderSignalType.RESPONSIBILITY,
            signal_key="responsibility",
            text="Folder matches its responsibility.",
            attributes={
                "responsibility_score": 0.8,
                "basis": "name and documents",
            },
            evidence=({"kind": "folder_summary"},),
            confidence=0.7,
            extractor_name="folder_evaluator",
            extractor_version="prompt-v1",
            index_input_digest="folder-signal-input-v1",
        )

        self.assertEqual(
            signal.signal_id,
            folder_signal_id(
                tenant="tenant-1",
                folder_id="folder-1",
                index_input_digest="folder-signal-input-v1",
                signal_type=FolderSignalType.RESPONSIBILITY,
                signal_key="responsibility",
            ),
        )
        self.assertEqual(signal.attributes["responsibility_score"], 0.8)

    def test_retrieved_folder_is_plain_reference(self) -> None:
        folder = RetrievedFolder(
            tenant="tenant-1",
            folder_id="folder-1",
            source_version="folder-v1",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
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
