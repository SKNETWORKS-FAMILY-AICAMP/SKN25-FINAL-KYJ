from __future__ import annotations

import unittest

from foldmind_ai_core.core.domain.models.workflow.actions import (
    CreateDocumentInput,
    CreateDocumentOutput,
    CreateFolderInput,
    CreateFolderOutput,
    HostAction,
    HostActionPolicy,
    HostActionResult,
    HostActionResultType,
    HostActionStatus,
    HostActionType,
    LinkDocumentsInput,
)
from foldmind_ai_core.core.domain.services.workflow import (
    apply_successful_host_action_output,
    host_action_status_for_result,
    validate_host_action_result_for_action,
)
from foldmind_ai_core.shared.validation import InvalidInputError


class WorkflowActionTests(unittest.TestCase):
    def test_host_action_policy_rejects_malformed_attempt_limits(self) -> None:
        with self.assertRaises(InvalidInputError):
            HostActionPolicy(max_attempts=True)
        with self.assertRaises(InvalidInputError):
            HostActionPolicy(max_attempts=0)
        with self.assertRaises(InvalidInputError):
            HostActionPolicy(max_attempts=-1)

    def test_host_action_rejects_malformed_attempt_count(self) -> None:
        with self.assertRaises(InvalidInputError):
            HostAction(
                action_type=HostActionType.CREATE_FOLDER,
                summary="Create folder.",
                input=CreateFolderInput(name="Projects"),
                attempts=True,
            )
        with self.assertRaises(InvalidInputError):
            HostAction(
                action_type=HostActionType.CREATE_FOLDER,
                summary="Create folder.",
                input=CreateFolderInput(name="Projects"),
                attempts=-1,
            )

    def test_host_action_result_validation_is_a_domain_rule(self) -> None:
        action = HostAction(
            action_type=HostActionType.CREATE_FOLDER,
            summary="Create folder.",
            input=CreateFolderInput(name="Projects"),
        )
        with self.assertRaises(InvalidInputError):
            validate_host_action_result_for_action(
                action,
                HostActionResult(
                    action_id=action.action_id,
                    action_type=HostActionType.CREATE_DOCUMENT,
                    outcome=HostActionResultType.APPROVED,
                ),
            )
        with self.assertRaises(InvalidInputError):
            validate_host_action_result_for_action(
                action,
                HostActionResult(
                    action_id=action.action_id,
                    outcome=HostActionResultType.SUCCEEDED,
                ),
            )

        action.status = HostActionStatus.READY
        with self.assertRaises(InvalidInputError):
            validate_host_action_result_for_action(
                action,
                HostActionResult(
                    action_id=action.action_id,
                    outcome=HostActionResultType.SUCCEEDED,
                    error="unexpected error",
                ),
            )

    def test_host_action_status_transition_is_a_domain_rule(self) -> None:
        action = HostAction(
            action_type=HostActionType.CREATE_FOLDER,
            summary="Create folder.",
            input=CreateFolderInput(name="Projects"),
            policy=HostActionPolicy(max_attempts=2, retryable=True),
            status=HostActionStatus.READY,
            attempts=1,
        )
        status = host_action_status_for_result(
            action,
            HostActionResult(
                action_id=action.action_id,
                outcome=HostActionResultType.FAILED,
            ),
        )

        self.assertEqual(status, HostActionStatus.READY)

    def test_successful_create_folder_output_updates_later_document_placeholder(
        self,
    ) -> None:
        create_folder = HostAction(
            action_type=HostActionType.CREATE_FOLDER,
            summary="Create folder.",
            input=CreateFolderInput(name="Projects"),
            status=HostActionStatus.READY,
        )
        earlier_create_document = HostAction(
            action_type=HostActionType.CREATE_DOCUMENT,
            summary="Create earlier document.",
            input=CreateDocumentInput(
                title="Old plan",
                body="Body",
                metadata={"folder_action_id": create_folder.action_id},
            ),
        )
        create_document = HostAction(
            action_type=HostActionType.CREATE_DOCUMENT,
            summary="Create document.",
            input=CreateDocumentInput(
                title="Plan",
                body="Body",
                metadata={"folder_action_id": create_folder.action_id},
            ),
        )

        error = apply_successful_host_action_output(
            create_folder,
            [earlier_create_document, create_folder, create_document],
            HostActionResult(
                action_id=create_folder.action_id,
                outcome=HostActionResultType.SUCCEEDED,
                output=CreateFolderOutput(folder_id="folder-1"),
            ),
        )

        self.assertIsNone(error)
        self.assertIsNone(earlier_create_document.input.folder_id)
        self.assertEqual(create_document.input.folder_id, "folder-1")

    def test_successful_create_document_output_updates_later_link_placeholder(
        self,
    ) -> None:
        create_document = HostAction(
            action_type=HostActionType.CREATE_DOCUMENT,
            summary="Create document.",
            input=CreateDocumentInput(title="Plan", body="Body"),
            status=HostActionStatus.READY,
        )
        link_documents = HostAction(
            action_type=HostActionType.LINK_DOCUMENTS,
            summary="Link document.",
            input=LinkDocumentsInput(
                source_type="document",
                source_id=create_document.action_id,
                target_type="document",
                target_id="target-doc",
            ),
        )

        error = apply_successful_host_action_output(
            create_document,
            [create_document, link_documents],
            HostActionResult(
                action_id=create_document.action_id,
                outcome=HostActionResultType.SUCCEEDED,
                output=CreateDocumentOutput(
                    created_document_type="note",
                    created_document_id="doc-1",
                    source_version="v2",
                ),
            ),
        )

        self.assertIsNone(error)
        self.assertEqual(link_documents.input.source_type, "note")
        self.assertEqual(link_documents.input.source_id, "doc-1")
        self.assertEqual(link_documents.input.metadata["source_version"], "v2")


if __name__ == "__main__":
    unittest.main()
