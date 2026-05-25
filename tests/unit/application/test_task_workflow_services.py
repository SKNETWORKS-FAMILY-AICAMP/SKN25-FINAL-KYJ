from __future__ import annotations

import unittest
from contextlib import asynccontextmanager

from foldmind_ai_core.core.application.models.task_commands import (
    AppendTaskInputCommand,
    CreateTaskCommand,
)
from foldmind_ai_core.core.application.errors import (
    ConcurrentTaskUpdateError,
    ResourceNotFoundError,
)
from foldmind_ai_core.core.application.services.workflow.task_workflow_service import (
    TaskWorkflowService,
)
from foldmind_ai_core.core.domain.models.host_actions import (
    CreateFolderInput,
    HostAction,
    HostActionResult,
    HostActionStatus,
    HostActionType,
)
from foldmind_ai_core.core.domain.models.tasks import (
    TaskAnalysis,
    TaskContext,
    TaskSnapshot,
    TaskStatus,
)


class FakeTaskRepository:
    def __init__(self) -> None:
        self.created: list[TaskSnapshot] = []
        self.saved: list[TaskSnapshot] = []
        self.save_if_unchanged_result = True

    async def create(self, snapshot: TaskSnapshot) -> TaskSnapshot:
        self.created.append(snapshot)
        return snapshot

    async def get(self, *, task_id: str) -> TaskSnapshot | None:
        return None

    async def get_by_input_id(
        self,
        *,
        task_input_id: str,
    ) -> TaskSnapshot | None:
        return None

    async def get_by_action_id(
        self,
        *,
        action_id: str,
    ) -> TaskSnapshot | None:
        return None

    async def _save(self, snapshot: TaskSnapshot) -> None:
        self.saved.append(snapshot)

    async def save_if_unchanged(
        self,
        snapshot: TaskSnapshot,
        *,
        expected_snapshot: TaskSnapshot,
    ) -> bool:
        if not self.save_if_unchanged_result:
            return False
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


class FailingWorkflowRuntime:
    async def run(self, snapshot: TaskSnapshot) -> TaskSnapshot:
        snapshot.status = TaskStatus.FAILED
        snapshot.error = "Tool failed."
        snapshot.analysis = TaskAnalysis(message="Task failed.")
        return snapshot

    async def resume_from_action_result(
        self,
        *,
        task_id: str,
        result: HostActionResult,
    ) -> TaskSnapshot:
        raise AssertionError("resume_from_action_result should not be called")


class RaisingWorkflowRuntime:
    async def run(self, snapshot: TaskSnapshot) -> TaskSnapshot:
        action = HostAction(
            action_type=HostActionType.CREATE_FOLDER,
            summary="Create folder.",
            input=CreateFolderInput(name="Projects"),
            action_id="11111111-1111-4111-8111-111111111111",
            status=HostActionStatus.READY,
        )
        snapshot.host_actions = [action]
        snapshot.current_action_id = action.action_id
        raise RuntimeError("Graph crashed.")

    async def resume_from_action_result(
        self,
        *,
        task_id: str,
        result: HostActionResult,
    ) -> TaskSnapshot:
        raise AssertionError("resume_from_action_result should not be called")


class TaskWorkflowApplicationServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_workflow_failure_status_is_not_overwritten_by_result_marking(
        self,
    ) -> None:
        repository = FakeTaskRepository()
        session_provider = FakeTaskSessionProvider(repository)
        service = TaskWorkflowService(
            tasks=session_provider,
            workflow=FailingWorkflowRuntime(),
        )

        snapshot = await service.create_task(
            CreateTaskCommand(
                tenant="tenant-1",
                request="Run a workflow that fails.",
                context=TaskContext(
                    requested_at="2026-05-17T09:30:00+09:00"
                ),
            )
        )

        self.assertEqual(snapshot.status, TaskStatus.FAILED)
        self.assertEqual(snapshot.error, "Tool failed.")
        self.assertEqual(snapshot.analysis.message, "Task failed.")
        self.assertEqual(len(repository.saved), 1)
        self.assertEqual(repository.saved[0].status, TaskStatus.FAILED)

    async def test_unhandled_workflow_exception_clears_current_action(self) -> None:
        repository = FakeTaskRepository()
        session_provider = FakeTaskSessionProvider(repository)
        service = TaskWorkflowService(
            tasks=session_provider,
            workflow=RaisingWorkflowRuntime(),
        )

        snapshot = await service.create_task(
            CreateTaskCommand(
                tenant="tenant-1",
                request="Run a workflow that crashes.",
                context=TaskContext(
                    requested_at="2026-05-17T09:30:00+09:00"
                ),
            )
        )

        self.assertEqual(snapshot.status, TaskStatus.FAILED)
        self.assertEqual(snapshot.error, "Graph crashed.")
        self.assertIsNone(snapshot.current_action_id)
        self.assertEqual(snapshot.host_actions[0].status, HostActionStatus.FAILED)
        self.assertEqual(len(repository.saved), 1)
        self.assertEqual(repository.saved[0].status, TaskStatus.FAILED)

    async def test_append_to_missing_task_raises_not_found(self) -> None:
        repository = FakeTaskRepository()
        session_provider = FakeTaskSessionProvider(repository)
        service = TaskWorkflowService(
            tasks=session_provider,
            workflow=FailingWorkflowRuntime(),
        )

        with self.assertRaises(ResourceNotFoundError):
            await service.append_task_input(
                AppendTaskInputCommand(
                    task_id="55555555-5555-4555-8555-555555555555",
                    request="Follow-up request.",
                    context=TaskContext(
                        requested_at="2026-05-17T09:30:00+09:00"
                    ),
                )
            )

        self.assertEqual(repository.saved, [])

    async def test_concurrent_task_update_is_not_overwritten(self) -> None:
        repository = FakeTaskRepository()
        repository.save_if_unchanged_result = False
        session_provider = FakeTaskSessionProvider(repository)
        service = TaskWorkflowService(
            tasks=session_provider,
            workflow=FailingWorkflowRuntime(),
        )

        with self.assertRaises(ConcurrentTaskUpdateError):
            await service.create_task(
                CreateTaskCommand(
                    tenant="tenant-1",
                    request="Run a workflow that races.",
                    context=TaskContext(
                        requested_at="2026-05-17T09:30:00+09:00"
                    ),
                )
            )

        self.assertEqual(repository.saved, [])


if __name__ == "__main__":
    unittest.main()
