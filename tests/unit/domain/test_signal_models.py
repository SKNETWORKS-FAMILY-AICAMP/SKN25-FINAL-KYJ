from __future__ import annotations

import unittest

from foldmind_ai_core.core.domain.models.document_signals import (
    DocumentSignalEvidence,
    DocumentSignalType,
)
from foldmind_ai_core.core.domain.models.folder_signals import FolderSignalType
from foldmind_ai_core.core.domain.services.document_signal_service import (
    DEFAULT_DOCUMENT_SIGNAL_TYPES,
    DocumentSignalService,
)
from foldmind_ai_core.core.domain.services.folder_signal_service import FolderSignalService
from foldmind_ai_core.shared.validation import InvalidInputError


class SignalDomainModelTests(unittest.TestCase):
    def test_signal_confidence_fields_reject_out_of_range_values(self) -> None:
        with self.assertRaises(InvalidInputError):
            DocumentSignalService().create(
                tenant="tenant-1",
                document_type="document",
                document_id="doc-1",
                source_version="v1",
                document_signal_input_digest="index-input-v1",
                signal_type=DocumentSignalType.CONCEPT,
                text="Startup",
                attributes={"label": "Startup"},
                evidence=(DocumentSignalEvidence(chunk_id="chunk-1", quote="Startup"),),
                confidence=1.1,
                extractor_name="document_signal_extractor",
                extractor_version="prompt-v1",
            )

    def test_document_signal_requires_supported_type_text_and_evidence(self) -> None:
        with self.assertRaises(InvalidInputError):
            DocumentSignalService().create(
                tenant="tenant-1",
                document_type="document",
                document_id="doc-1",
                source_version="v1",
                document_signal_input_digest="index-input-v1",
                signal_type="unsupported",
                text="Unsupported",
                attributes={},
                evidence=(DocumentSignalEvidence(chunk_id="chunk-1", quote="quote"),),
                confidence=0.8,
                extractor_name="document_signal_extractor",
                extractor_version="prompt-v1",
            )

        with self.assertRaises(InvalidInputError):
            DocumentSignalService().create(
                tenant="tenant-1",
                document_type="document",
                document_id="doc-1",
                source_version="v1",
                document_signal_input_digest="index-input-v1",
                signal_type=DocumentSignalType.SUMMARY,
                text=" ",
                attributes={},
                evidence=(DocumentSignalEvidence(chunk_id="chunk-1", quote="quote"),),
                extractor_name="document_signal_extractor",
                extractor_version="prompt-v1",
                confidence=0.8,
            )

        with self.assertRaises(InvalidInputError):
            DocumentSignalService().create(
                tenant="tenant-1",
                document_type="document",
                document_id="doc-1",
                source_version="v1",
                document_signal_input_digest="index-input-v1",
                signal_type=DocumentSignalType.SUMMARY,
                text="Summary",
                attributes={"bad": object()},
                evidence=(DocumentSignalEvidence(chunk_id="chunk-1", quote="quote"),),
                extractor_name="document_signal_extractor",
                extractor_version="prompt-v1",
                confidence=0.8,
            )

        with self.assertRaises(InvalidInputError):
            DocumentSignalService().create(
                tenant="tenant-1",
                document_type="document",
                document_id="doc-1",
                source_version="v1",
                document_signal_input_digest="index-input-v1",
                signal_type=DocumentSignalType.SUMMARY,
                text="Summary",
                attributes={},
                evidence=(),
                extractor_name="document_signal_extractor",
                extractor_version="prompt-v1",
                confidence=0.8,
            )

    def test_document_signal_create_normalizes_required_text_fields(self) -> None:
        signal = DocumentSignalService().create(
            tenant=" tenant-1 ",
            document_type="document",
            document_id=" doc-1 ",
            source_version=" v1 ",
            document_signal_input_digest=" signal-input-v1 ",
            signal_type=DocumentSignalType.SUMMARY,
            text=" Summary ",
            attributes={},
            evidence=(DocumentSignalEvidence(chunk_id=" chunk-1 ", quote=" quote "),),
            confidence=0.8,
            extractor_name=" document_signal_extractor ",
            extractor_version=" prompt-v1 ",
            signal_generation_version=" signals-v1 ",
        )

        self.assertEqual(signal.tenant, "tenant-1")
        self.assertEqual(signal.document_id, "doc-1")
        self.assertEqual(signal.source_version, "v1")
        self.assertEqual(signal.document_signal_input_digest, "signal-input-v1")
        self.assertEqual(signal.signal_generation_version, "signals-v1")
        self.assertEqual(signal.signal_type, DocumentSignalType.SUMMARY)
        self.assertEqual(signal.text, "Summary")
        self.assertEqual(signal.evidence[0].chunk_id, "chunk-1")
        self.assertEqual(signal.evidence[0].quote, "quote")
        self.assertEqual(signal.extractor_name, "document_signal_extractor")
        self.assertEqual(signal.extractor_version, "prompt-v1")

    def test_signal_id_is_deterministic_for_same_index_input_digest_type_and_key(self) -> None:
        first = DocumentSignalService().signal_id(
            tenant="tenant-1",
            document_id="doc-1",
            document_signal_input_digest="index-input-v1",
            signal_type=DocumentSignalType.CONCEPT,
            signal_key="startup",
        )
        second = DocumentSignalService().signal_id(
            tenant="tenant-1",
            document_id="doc-1",
            document_signal_input_digest="index-input-v1",
            signal_type="concept",
            signal_key="startup",
        )

        self.assertEqual(first, second)

    def test_signal_id_ignores_document_type_identity(self) -> None:
        first_signal_id = DocumentSignalService().signal_id(
            tenant="tenant-1",
            document_id="doc-1",
            document_signal_input_digest="index-input-v1",
            signal_type=DocumentSignalType.CONCEPT,
            signal_key="startup",
        )
        second_signal_id = DocumentSignalService().signal_id(
            tenant="tenant-1",
            document_id="doc-1",
            document_signal_input_digest="index-input-v1",
            signal_type=DocumentSignalType.CONCEPT,
            signal_key="startup",
        )

        self.assertEqual(first_signal_id, second_signal_id)

    def test_summary_and_concept_are_allowed_document_signals(self) -> None:
        self.assertIn(DocumentSignalType.SUMMARY, DEFAULT_DOCUMENT_SIGNAL_TYPES)
        self.assertIn(DocumentSignalType.CONCEPT, DEFAULT_DOCUMENT_SIGNAL_TYPES)

    def test_folder_signal_attributes_and_identity_are_supported(self) -> None:
        signal = FolderSignalService().create(
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
            folder_signal_input_digest="folder-signal-input-v1",
        )

        self.assertEqual(
            signal.signal_id,
            FolderSignalService().signal_id(
                tenant="tenant-1",
                folder_id="folder-1",
                folder_signal_input_digest="folder-signal-input-v1",
                signal_type=FolderSignalType.RESPONSIBILITY,
                signal_key="responsibility",
            ),
        )
        self.assertEqual(signal.attributes["responsibility_score"], 0.8)

    def test_folder_signal_create_normalizes_required_text_fields(self) -> None:
        signal = FolderSignalService().create(
            tenant=" tenant-1 ",
            folder_id=" folder-1 ",
            source_version=" v1 ",
            signal_type=FolderSignalType.RESPONSIBILITY,
            signal_key=" responsibility ",
            text=" Folder matches its responsibility. ",
            related_document_id=" doc-1 ",
            attributes={},
            evidence=({"kind": "folder_summary"},),
            confidence=0.7,
            extractor_name=" folder_evaluator ",
            extractor_version=" prompt-v1 ",
            folder_signal_input_digest=" folder-signal-input-v1 ",
            signal_generation_version=" signals-v1 ",
        )

        self.assertEqual(signal.tenant, "tenant-1")
        self.assertEqual(signal.folder_id, "folder-1")
        self.assertEqual(signal.source_version, "v1")
        self.assertEqual(signal.folder_signal_input_digest, "folder-signal-input-v1")
        self.assertEqual(signal.signal_generation_version, "signals-v1")
        self.assertEqual(signal.signal_type, FolderSignalType.RESPONSIBILITY)
        self.assertEqual(signal.signal_key, "responsibility")
        self.assertEqual(signal.text, "Folder matches its responsibility.")
        self.assertEqual(signal.related_document_id, "doc-1")
        self.assertEqual(signal.extractor_name, "folder_evaluator")
        self.assertEqual(signal.extractor_version, "prompt-v1")

        with self.assertRaises(InvalidInputError):
            FolderSignalService().signal_id(
                tenant="tenant-1",
                folder_id="folder-1",
                folder_signal_input_digest="folder-signal-input-v1",
                signal_type=FolderSignalType.RESPONSIBILITY,
                signal_key="responsibility",
                related_document_id=123,  # type: ignore[arg-type]
            )

        with self.assertRaises(InvalidInputError):
            FolderSignalService().signal_id(
                tenant="tenant-1",
                folder_id="folder-1",
                folder_signal_input_digest="folder-signal-input-v1",
                signal_type=FolderSignalType.RESPONSIBILITY,
                signal_key="responsibility",
                related_document_id=" ",
            )

    def test_folder_signal_rejects_malformed_json_payloads(self) -> None:
        with self.assertRaises(InvalidInputError):
            FolderSignalService().create(
                tenant="tenant-1",
                folder_id="folder-1",
                source_version="v1",
                signal_type=FolderSignalType.RESPONSIBILITY,
                signal_key="responsibility",
                text="Folder matches its responsibility.",
                attributes={"bad": object()},
                evidence=({"kind": "folder_summary"},),
                confidence=0.7,
                extractor_name="folder_evaluator",
                extractor_version="prompt-v1",
                folder_signal_input_digest="folder-signal-input-v1",
            )

        with self.assertRaises(InvalidInputError):
            FolderSignalService().create(
                tenant="tenant-1",
                folder_id="folder-1",
                source_version="v1",
                signal_type=FolderSignalType.RESPONSIBILITY,
                signal_key="responsibility",
                text="Folder matches its responsibility.",
                attributes={},
                evidence=(["not", "an", "object"],),  # type: ignore[arg-type]
                confidence=0.7,
                extractor_name="folder_evaluator",
                extractor_version="prompt-v1",
                folder_signal_input_digest="folder-signal-input-v1",
            )

if __name__ == "__main__":
    unittest.main()
