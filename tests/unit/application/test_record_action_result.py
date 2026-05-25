from __future__ import annotations

import unittest
from contextlib import asynccontextmanager

from foldmind_ai_core.core.application.models.task_commands import (
    RecordActionResultCommand,
)
from foldmind_ai_core.core.application.services.workflow.task_workflow_service import (
    TaskWorkflowService,
)
from foldmind_ai_core.core.domain.models.host_actions import (
    CreateFolderInput,
    CreateFolderOutput,
    HostAction,
    HostActionResult,
    HostActionResultType,
    HostActionStatus,
    HostActionType,
)
from foldmind_ai_core.core.domain.models.tasks import (
    TaskAnalysis,
    TaskContext,
    TaskSnapshot,
    TaskStatus,
)
from foldmind_ai_core.shared.validation import InvalidInputError

ACTION_ID = "action-1"
TASK_ID = "task-1"


class FakeTaskRepository:
    def __init__(self, snapshot: TaskSnapshot | None) -> None:
        self.snapshot = snapshot
        self.saved: list[TaskSnapshot] = []

    async def create(self, snapshot: TaskSnapshot) -> TaskSnapshot:
        raise AssertionError("Task creation is not expected.")

    async def get(self, *, task_id: str) -> TaskSnapshot | None:
        raise AssertionError("Task lookup by id is not expected.")

    async def get_by_input_id(
        self,
        *,
        task_input_id: str,
    ) -> TaskSnapshot | None:
        raise AssertionError("Task lookup by input is not expected.")

    async def get_by_action_id(
        self,
        *,
        action_id: str,
    ) -> TaskSnapshot | None:
        if self.snapshot is None:
            return None
        return self.snapshot

    async def _save(self, snapshot: TaskSnapshot) -> None:
        self.saved.append(snapshot)

    async def save_if_unchanged(
        self,
        snapshot: TaskSnapshot,
        *,
        expected_snapshot: TaskSnapshot,
    ) -> bool:
        await self._save(snapshot)
        return True


class FakeTaskSession:
    def __init__(self, tasks: FakeTaskRepository) -> None:
        self.tasks = tasks


class FakeTaskSessionProvider:
    def __init__(self, tasks: FakeTaskRepository) -> None:
        self.tasks = tasks

    @asynccontextmanager
    async def session(self):
        yield FakeTaskSession(self.tasks)

    @asynccontextmanager
    async def transaction(self):
        yield FakeTaskSession(self.tasks)


class FakeWorkflowRuntime:
    def __init__(self, snapshot: TaskSnapshot) -> None:
        self.snapshot = snapshot
        self.results: list[HostActionResult] = []

    async def run(self, snapshot: TaskSnapshot) -> TaskSnapshot:
        raise AssertionError("Workflow run is not expected.")

    async def resume_from_action_result(
        self,
        *,
        task_id: str,
        result: HostActionResult,
    ) -> TaskSnapshot:
        self.results.append(result)
        return self.snapshot


class RecordActionResultServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_action_type_mismatch_before_resuming_workflow(self) -> None:
        snapshot = _snapshot(action_status=HostActionStatus.READY)
        repository = FakeTaskRepository(snapshot)
        workflow = FakeWorkflowRuntime(snapshot)
        service = TaskWorkflowService(
            tasks=FakeTaskSessionProvider(repository),
            workflow=workflow,
        )

        with self.assertRaises(InvalidInputError):
            await service.record_action_result(
                RecordActionResultCommand(
                    result=HostActionResult(
                        action_id=ACTION_ID,
                        action_type=HostActionType.CREATE_DOCUMENT,
                        outcome=HostActionResultType.SUCCEEDED,
                    ),
                )
            )

        self.assertEqual(workflow.results, [])
        self.assertEqual(repository.saved, [])

    async def test_accepts_matching_action_type(self) -> None:
        snapshot = _snapshot(action_status=HostActionStatus.READY)
        repository = FakeTaskRepository(snapshot)
        workflow = FakeWorkflowRuntime(snapshot)
        service = TaskWorkflowService(
            tasks=FakeTaskSessionProvider(repository),
            workflow=workflow,
        )
        result = HostActionResult(
            action_id=ACTION_ID,
            action_type=HostActionType.CREATE_FOLDER,
            outcome=HostActionResultType.SUCCEEDED,
        )

        returned = await service.record_action_result(
            RecordActionResultCommand(result=result)
        )

        self.assertEqual(returned.task.task_id, snapshot.task_id)
        self.assertEqual(len(workflow.results), 1)
        self.assertEqual(workflow.results[0].action_id, result.action_id)
        self.assertEqual(workflow.results[0].action_type, HostActionType.CREATE_FOLDER)
        self.assertEqual(workflow.results[0].outcome, HostActionResultType.SUCCEEDED)
        self.assertEqual(repository.saved, [snapshot])

    async def test_rejects_contradictory_result_payload_before_resuming_workflow(
        self,
    ) -> None:
        snapshot = _snapshot(action_status=HostActionStatus.READY)
        repository = FakeTaskRepository(snapshot)
        workflow = FakeWorkflowRuntime(snapshot)
        service = TaskWorkflowService(
            tasks=FakeTaskSessionProvider(repository),
            workflow=workflow,
        )

        with self.assertRaises(InvalidInputError):
            await service.record_action_result(
                RecordActionResultCommand(
                    result=HostActionResult(
                        action_id=ACTION_ID,
                        action_type=HostActionType.CREATE_FOLDER,
                        outcome=HostActionResultType.SUCCEEDED,
                        error="Unexpected error.",
                    ),
                )
            )
        with self.assertRaises(InvalidInputError):
            await service.record_action_result(
                RecordActionResultCommand(
                    result=HostActionResult(
                        action_id=ACTION_ID,
                        action_type=HostActionType.CREATE_FOLDER,
                        outcome=HostActionResultType.FAILED,
                        output=CreateFolderOutput(folder_id="folder-1"),
                    ),
                )
            )

        self.assertEqual(workflow.results, [])
        self.assertEqual(repository.saved, [])

    async def test_rejects_execution_result_for_proposed_action(self) -> None:
        snapshot = _snapshot(action_status=HostActionStatus.PROPOSED)
        repository = FakeTaskRepository(snapshot)
        workflow = FakeWorkflowRuntime(snapshot)
        service = TaskWorkflowService(
            tasks=FakeTaskSessionProvider(repository),
            workflow=workflow,
        )

        with self.assertRaises(InvalidInputError):
            await service.record_action_result(
                RecordActionResultCommand(
                    result=HostActionResult(
                        action_id=ACTION_ID,
                        action_type=HostActionType.CREATE_FOLDER,
                        outcome=HostActionResultType.SUCCEEDED,
                    ),
                )
            )

        self.assertEqual(workflow.results, [])
        self.assertEqual(repository.saved, [])

    async def test_rejects_result_for_terminal_action(self) -> None:
        snapshot = _snapshot(
            action_status=HostActionStatus.SUCCEEDED,
            task_status=TaskStatus.COMPLETED,
        )
        repository = FakeTaskRepository(snapshot)
        workflow = FakeWorkflowRuntime(snapshot)
        service = TaskWorkflowService(
            tasks=FakeTaskSessionProvider(repository),
            workflow=workflow,
        )

        with self.assertRaises(InvalidInputError):
            await service.record_action_result(
                RecordActionResultCommand(
                    result=HostActionResult(
                        action_id=ACTION_ID,
                        action_type=HostActionType.CREATE_FOLDER,
                        outcome=HostActionResultType.FAILED,
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
