from __future__ import annotations

import unittest
import uuid

from foldmind_ai_core.application.workflows.host_actions.builder import HostActionBuilder
from foldmind_ai_core.domain.generation.results import (
    FolderRecommendation,
    FolderRecommendationResult,
)
from foldmind_ai_core.domain.workflow.actions import HostActionType, MoveDocumentInput
from foldmind_ai_core.domain.workflow.tasks import TaskAnalysis, TaskSnapshot, TaskStatus


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


def _task(*, metadata: dict[str, object] | None = None) -> TaskSnapshot:
    return TaskSnapshot(
        task_id=TASK_ID,
        tenant="tenant-1",
        request="Move this document.",
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
