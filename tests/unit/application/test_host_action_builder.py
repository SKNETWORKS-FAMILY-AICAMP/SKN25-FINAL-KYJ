from __future__ import annotations

import unittest
import uuid

from foldmind_ai_core.core.application.workflows.host_actions.builder import HostActionBuilder
from foldmind_ai_core.core.domain.models.generation.results import (
    DraftResult,
    FolderRecommendation,
    FolderRecommendationResult,
    GeneratedTextResult,
)
from foldmind_ai_core.core.domain.models.workflow.actions import (
    CreateDocumentInput,
    HostActionStatus,
    HostActionType,
    MoveDocumentInput,
)
from foldmind_ai_core.core.domain.models.workflow.tasks import TaskAnalysis, TaskContext, TaskSnapshot, TaskStatus

DOCUMENT_ID = "11111111-1111-4111-8111-111111111111"
FOLDER_ID = "22222222-2222-4222-8222-222222222222"
TASK_ID = "55555555-5555-4555-8555-555555555555"


class HostActionBuilderTests(unittest.TestCase):
    def test_existing_document_actions_require_canonical_document_id(self) -> None:
        task = _task()
        recommendation = _folder_recommendation()
        builder = HostActionBuilder()

        move_plan = builder.build(
            task=task,
            folder_recommendation=recommendation,
            requested_actions=(HostActionType.MOVE_DOCUMENT,),
        )
        update_plan = builder.build(
            task=task,
            requested_actions=(HostActionType.UPDATE_DOCUMENT,),
            options={"title": "Updated title"},
        )

        self.assertEqual(move_plan.host_actions, [])
        self.assertEqual(update_plan.host_actions, [])

    def test_existing_document_action_uses_metadata_document_id(self) -> None:
        task = _task(
            metadata={
                "document": {
                    "document_type": "note",
                    "document_id": DOCUMENT_ID,
                }
            }
        )
        plan = HostActionBuilder().build(
            task=task,
            folder_recommendation=_folder_recommendation(),
            requested_actions=(HostActionType.MOVE_DOCUMENT,),
        )

        self.assertEqual(len(plan.host_actions), 1)
        action = plan.host_actions[0]
        self.assertIsNotNone(action.action_id)
        uuid.UUID(action.action_id or "")
        self.assertIsInstance(action.input, MoveDocumentInput)
        self.assertEqual(action.input.document_type, "note")
        self.assertEqual(action.input.document_id, DOCUMENT_ID)
        self.assertEqual(action.input.target_folder_id, FOLDER_ID)

    def test_created_document_waits_for_requested_created_folder(self) -> None:
        plan = HostActionBuilder().build(
            task=_task(),
            folder_recommendation=_folder_recommendation(),
            requested_actions=(
                HostActionType.CREATE_FOLDER,
                HostActionType.CREATE_DOCUMENT,
            ),
            options={"body": "Draft body"},
        )

        create_folder_action = plan.host_actions[0]
        create_document_action = plan.host_actions[1]

        self.assertEqual(create_folder_action.action_type, HostActionType.CREATE_FOLDER)
        self.assertEqual(
            create_document_action.action_type,
            HostActionType.CREATE_DOCUMENT,
        )
        self.assertIsInstance(create_document_action.input, CreateDocumentInput)
        self.assertIsNone(create_document_action.input.folder_id)
        self.assertEqual(
            create_document_action.input.metadata["folder_action_id"],
            create_folder_action.action_id,
        )
        self.assertEqual(create_folder_action.status, HostActionStatus.PROPOSED)
        self.assertEqual(create_document_action.status, HostActionStatus.PROPOSED)

    def test_create_document_ignores_blank_generated_body(self) -> None:
        builder = HostActionBuilder()

        draft_plan = builder.build(
            task=_task(),
            requested_actions=(HostActionType.CREATE_DOCUMENT,),
            draft=DraftResult(draft="   "),
        )
        summary_plan = builder.build(
            task=_task(),
            requested_actions=(HostActionType.CREATE_DOCUMENT,),
            summary=GeneratedTextResult(text="   "),
        )

        self.assertEqual(draft_plan.host_actions, [])
        self.assertEqual(summary_plan.host_actions, [])

    def test_host_action_policy_uses_typed_boolean_options(self) -> None:
        task = _task()
        builder = HostActionBuilder()

        plan = builder.build(
            task=task,
            requested_actions=(HostActionType.CREATE_FOLDER,),
            options={
                "allow_skip": True,
                "retryable": False,
                "requires_confirmation": False,
                "max_attempts": 3,
            },
        )
        policy = plan.host_actions[0].policy

        self.assertTrue(policy.allow_skip)
        self.assertFalse(policy.retryable)
        self.assertFalse(policy.requires_confirmation)
        self.assertEqual(policy.max_attempts, 3)
        self.assertEqual(plan.host_actions[0].status, HostActionStatus.READY)

        with self.assertRaises(TypeError):
            builder.build(
                task=task,
                requested_actions=(HostActionType.CREATE_FOLDER,),
                options={"allow_skip": "true"},
            )
        with self.assertRaises(TypeError):
            builder.build(
                task=task,
                requested_actions=(HostActionType.CREATE_FOLDER,),
                options={"retryable": "false"},
            )
        with self.assertRaises(TypeError):
            builder.build(
                task=task,
                requested_actions=(HostActionType.CREATE_FOLDER,),
                options={"requires_confirmation": "false"},
            )
        with self.assertRaises(TypeError):
            builder.build(
                task=task,
                requested_actions=(HostActionType.CREATE_FOLDER,),
                options={"max_attempts": True},
            )
        with self.assertRaises(TypeError):
            builder.build(
                task=task,
                requested_actions=(HostActionType.CREATE_FOLDER,),
                options={"max_attempts": "3"},
            )
        with self.assertRaises(ValueError):
            builder.build(
                task=task,
                requested_actions=(HostActionType.CREATE_FOLDER,),
                options={"max_attempts": 0},
            )

    def test_update_document_rejects_non_object_metadata_option(self) -> None:
        task = _task(
            metadata={
                "document": {
                    "document_type": "note",
                    "document_id": DOCUMENT_ID,
                }
            }
        )

        with self.assertRaises(TypeError):
            HostActionBuilder().build(
                task=task,
                requested_actions=(HostActionType.UPDATE_DOCUMENT,),
                options={"metadata": ["invalid"]},
            )

    def test_host_action_builder_rejects_non_string_text_options(self) -> None:
        builder = HostActionBuilder()
        task = _task(
            metadata={
                "document": {
                    "document_type": "note",
                    "document_id": DOCUMENT_ID,
                }
            }
        )

        invalid_cases = (
            (HostActionType.CREATE_FOLDER, {"folder_name": 123}),
            (HostActionType.CREATE_FOLDER, {"topic": 123}),
            (HostActionType.CREATE_DOCUMENT, {"body": 123}),
            (HostActionType.UPDATE_DOCUMENT, {"title": 123}),
            (HostActionType.MOVE_DOCUMENT, {"source_folder_id": 123}),
            (
                HostActionType.LINK_DOCUMENTS,
                {
                    "target_type": "document",
                    "target_id": "doc-2",
                    "relationship": 123,
                },
            ),
            (HostActionType.LINK_DOCUMENTS, {"target_type": 123, "target_id": "doc-2"}),
        )
        for action_type, options in invalid_cases:
            with self.subTest(action_type=action_type, options=options):
                with self.assertRaises(TypeError):
                    builder.build(
                        task=task,
                        folder_recommendation=_folder_recommendation(),
                        requested_actions=(action_type,),
                        options=options,
                    )

    def test_host_action_builder_rejects_non_string_document_metadata_ids(self) -> None:
        with self.assertRaises(TypeError):
            HostActionBuilder().build(
                task=_task(
                    metadata={
                        "document": {
                            "document_type": "note",
                            "document_id": 123,
                        }
                    }
                ),
                folder_recommendation=_folder_recommendation(),
                requested_actions=(HostActionType.MOVE_DOCUMENT,),
            )

def _task(*, metadata: dict[str, object] | None = None) -> TaskSnapshot:
    return TaskSnapshot(
        task_id=TASK_ID,
        tenant="tenant-1",
        request="Move this document.",
        context=TaskContext(requested_at="2026-05-17T09:30:00+09:00"),
        status=TaskStatus.CLARIFICATION_REQUIRED,
        analysis=TaskAnalysis(message="Planning."),
        metadata=metadata or {},
    )


def _folder_recommendation() -> FolderRecommendationResult:
    return FolderRecommendationResult(
        primary=FolderRecommendation(
            folder_id=FOLDER_ID,
            reason="Best folder.",
            score=0.9,
        )
    )


if __name__ == "__main__":
    unittest.main()
