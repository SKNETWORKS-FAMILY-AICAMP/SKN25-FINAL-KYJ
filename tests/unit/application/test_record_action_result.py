from __future__ import annotations

import unittest

from foldmind_ai_core.core.application.commands.workflow import (
    CreateFolderOutputCommand,
    HostActionResultCommand,
    RecordActionResultCommand,
)
from foldmind_ai_core.core.application.use_cases.workflow.record_action_result import (
    RecordActionResultUseCase,
)
from foldmind_ai_core.core.domain.models.workflow.actions import (
    CreateFolderInput,
    HostAction,
    HostActionResult,
    HostActionResultType,
    HostActionStatus,
    HostActionType,
)
from foldmind_ai_core.core.domain.models.workflow.tasks import TaskAnalysis, TaskContext, TaskSnapshot, TaskStatus
from foldmind_ai_core.shared.validation import InvalidInputError

ACTION_ID = "action-1"
TASK_ID = "task-1"


class FakeTaskRepository:
    def __init__(self, snapshot: TaskSnapshot | None) -> None:
        self.snapshot = snapshot
        self.saved: list[TaskSnapshot] = []

    def create(self, snapshot: TaskSnapshot) -> None:
        raise AssertionError("Task creation is not expected.")

    def get(self, *, task_id: str) -> TaskSnapshot | None:
        raise AssertionError("Task lookup by id is not expected.")

    def get_by_input_id(self, *, task_input_id: str) -> TaskSnapshot | None:
        raise AssertionError("Task lookup by input is not expected.")

    def get_by_action_id(self, *, action_id: str) -> TaskSnapshot | None:
        return self.snapshot

    def save(self, snapshot: TaskSnapshot) -> None:
        self.saved.append(snapshot)


class FakeWorkflowRuntime:
    def __init__(self, snapshot: TaskSnapshot) -> None:
        self.snapshot = snapshot
        self.results: list[HostActionResult] = []

    def run(self, snapshot: TaskSnapshot) -> TaskSnapshot:
        raise AssertionError("Workflow run is not expected.")

    def resume_from_action_result(
        self,
        *,
        task_id: str,
        result: HostActionResult,
    ) -> TaskSnapshot:
        self.results.append(result)
        return self.snapshot


class RecordActionResultUseCaseTests(unittest.TestCase):
    def test_rejects_action_type_mismatch_before_resuming_workflow(self) -> None:
        snapshot = _snapshot(action_status=HostActionStatus.READY)
        repository = FakeTaskRepository(snapshot)
        workflow = FakeWorkflowRuntime(snapshot)
        use_case = RecordActionResultUseCase(
            task_repository=repository,
            workflow=workflow,
        )

        with self.assertRaises(InvalidInputError):
            use_case.execute(
                RecordActionResultCommand(
                    result=HostActionResultCommand(
                        action_id=ACTION_ID,
                        action_type=HostActionType.CREATE_DOCUMENT.value,
                        outcome=HostActionResultType.SUCCEEDED.value,
                    ),
                )
            )

        self.assertEqual(workflow.results, [])
        self.assertEqual(repository.saved, [])

    def test_accepts_matching_action_type(self) -> None:
        snapshot = _snapshot(action_status=HostActionStatus.READY)
        repository = FakeTaskRepository(snapshot)
        workflow = FakeWorkflowRuntime(snapshot)
        use_case = RecordActionResultUseCase(
            task_repository=repository,
            workflow=workflow,
        )
        result = HostActionResultCommand(
            action_id=ACTION_ID,
            action_type=HostActionType.CREATE_FOLDER.value,
            outcome=HostActionResultType.SUCCEEDED.value,
        )

        returned = use_case.execute(RecordActionResultCommand(result=result))

        self.assertEqual(returned.task.task_id, snapshot.task_id)
        self.assertEqual(len(workflow.results), 1)
        self.assertEqual(workflow.results[0].action_id, result.action_id)
        self.assertEqual(workflow.results[0].action_type, HostActionType.CREATE_FOLDER)
        self.assertEqual(workflow.results[0].outcome, HostActionResultType.SUCCEEDED)
        self.assertEqual(repository.saved, [snapshot])

    def test_rejects_contradictory_result_payload_before_resuming_workflow(self) -> None:
        snapshot = _snapshot(action_status=HostActionStatus.READY)
        repository = FakeTaskRepository(snapshot)
        workflow = FakeWorkflowRuntime(snapshot)
        use_case = RecordActionResultUseCase(
            task_repository=repository,
            workflow=workflow,
        )

        with self.assertRaises(InvalidInputError):
            use_case.execute(
                RecordActionResultCommand(
                    result=HostActionResultCommand(
                        action_id=ACTION_ID,
                        action_type=HostActionType.CREATE_FOLDER.value,
                        outcome=HostActionResultType.SUCCEEDED.value,
                        error="Unexpected error.",
                    ),
                )
            )
        with self.assertRaises(InvalidInputError):
            use_case.execute(
                RecordActionResultCommand(
                    result=HostActionResultCommand(
                        action_id=ACTION_ID,
                        action_type=HostActionType.CREATE_FOLDER.value,
                        outcome=HostActionResultType.FAILED.value,
                        output=CreateFolderOutputCommand(folder_id="folder-1"),
                    ),
                )
            )

        self.assertEqual(workflow.results, [])
        self.assertEqual(repository.saved, [])

    def test_rejects_execution_result_for_proposed_action(self) -> None:
        snapshot = _snapshot(action_status=HostActionStatus.PROPOSED)
        repository = FakeTaskRepository(snapshot)
        workflow = FakeWorkflowRuntime(snapshot)
        use_case = RecordActionResultUseCase(
            task_repository=repository,
            workflow=workflow,
        )

        with self.assertRaises(InvalidInputError):
            use_case.execute(
                RecordActionResultCommand(
                    result=HostActionResultCommand(
                        action_id=ACTION_ID,
                        action_type=HostActionType.CREATE_FOLDER.value,
                        outcome=HostActionResultType.SUCCEEDED.value,
                    ),
                )
            )

        self.assertEqual(workflow.results, [])
        self.assertEqual(repository.saved, [])

    def test_rejects_result_for_terminal_action(self) -> None:
        snapshot = _snapshot(
            action_status=HostActionStatus.SUCCEEDED,
            task_status=TaskStatus.COMPLETED,
        )
        repository = FakeTaskRepository(snapshot)
        workflow = FakeWorkflowRuntime(snapshot)
        use_case = RecordActionResultUseCase(
            task_repository=repository,
            workflow=workflow,
        )

        with self.assertRaises(InvalidInputError):
            use_case.execute(
                RecordActionResultCommand(
                    result=HostActionResultCommand(
                        action_id=ACTION_ID,
                        action_type=HostActionType.CREATE_FOLDER.value,
                        outcome=HostActionResultType.FAILED.value,
                    ),
                )
            )

        self.assertEqual(workflow.results, [])
        self.assertEqual(repository.saved, [])


def _snapshot(
    *,
    action_status: HostActionStatus = HostActionStatus.PROPOSED,
    task_status: TaskStatus = TaskStatus.READY_FOR_HOST_ACTION,
) -> TaskSnapshot:
    return TaskSnapshot(
        task_id=TASK_ID,
        tenant="tenant-1",
        request="Create folder.",
        context=TaskContext(requested_at="2026-05-17T09:30:00+09:00"),
        status=task_status,
        analysis=TaskAnalysis(message="Ready."),
        host_actions=[
            HostAction(
                action_type=HostActionType.CREATE_FOLDER,
                summary="Create folder.",
                input=CreateFolderInput(name="Projects"),
                action_id=ACTION_ID,
                status=action_status,
            )
        ],
    )


if __name__ == "__main__":
    unittest.main()
