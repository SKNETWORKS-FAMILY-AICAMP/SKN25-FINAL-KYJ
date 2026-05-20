from __future__ import annotations

import unittest

from foldmind_ai_core.core.application.commands.workflow import (
    AppendTaskInputCommand,
    CreateTaskCommand,
    TaskRequestContextCommand,
)
from foldmind_ai_core.core.application.errors import ResourceNotFoundError
from foldmind_ai_core.core.application.use_cases.workflow.run_task import RunTaskUseCase
from foldmind_ai_core.core.domain.models.workflow.actions import (
    CreateFolderInput,
    HostAction,
    HostActionResult,
    HostActionStatus,
    HostActionType,
)
from foldmind_ai_core.core.domain.models.workflow.tasks import (
    TaskAnalysis,
    TaskSnapshot,
    TaskStatus,
)


class FakeTaskRepository:
    def __init__(self) -> None:
        self.created: list[TaskSnapshot] = []
        self.saved: list[TaskSnapshot] = []

    def create(self, snapshot: TaskSnapshot) -> None:
        self.created.append(snapshot)

    def get(self, *, task_id: str) -> TaskSnapshot | None:
        return None

    def get_by_input_id(self, *, task_input_id: str) -> TaskSnapshot | None:
        return None

    def get_by_action_id(self, *, action_id: str) -> TaskSnapshot | None:
        return None

    def save(self, snapshot: TaskSnapshot) -> None:
        self.saved.append(snapshot)


class FailingWorkflowRuntime:
    def run(self, snapshot: TaskSnapshot) -> TaskSnapshot:
        snapshot.status = TaskStatus.FAILED
        snapshot.error = "Tool failed."
        snapshot.analysis = TaskAnalysis(message="Task failed.")
        return snapshot

    def resume_from_action_result(
        self,
        *,
        task_id: str,
        result: HostActionResult,
    ) -> TaskSnapshot:
        raise AssertionError("resume_from_action_result should not be called")


class RaisingWorkflowRuntime:
    def run(self, snapshot: TaskSnapshot) -> TaskSnapshot:
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

    def resume_from_action_result(
        self,
        *,
        task_id: str,
        result: HostActionResult,
    ) -> TaskSnapshot:
        raise AssertionError("resume_from_action_result should not be called")


class RunTaskUseCaseTests(unittest.TestCase):
    def test_workflow_failure_status_is_not_overwritten_by_result_marking(self) -> None:
        repository = FakeTaskRepository()
        use_case = RunTaskUseCase(
            task_repository=repository,
            workflow=FailingWorkflowRuntime(),
        )

        snapshot = use_case.execute(
            CreateTaskCommand(
                tenant="tenant-1",
                request="Run a workflow that fails.",
                context=TaskRequestContextCommand(
                    requested_at="2026-05-17T09:30:00+09:00"
                ),
            )
        ).task

        self.assertEqual(snapshot.status, TaskStatus.FAILED)
        self.assertEqual(snapshot.error, "Tool failed.")
        self.assertEqual(snapshot.analysis.message, "Task failed.")
        self.assertEqual(len(repository.saved), 1)
        self.assertEqual(repository.saved[0].status, TaskStatus.FAILED)

    def test_unhandled_workflow_exception_clears_current_action(self) -> None:
        repository = FakeTaskRepository()
        use_case = RunTaskUseCase(
            task_repository=repository,
            workflow=RaisingWorkflowRuntime(),
        )

        snapshot = use_case.execute(
            CreateTaskCommand(
                tenant="tenant-1",
                request="Run a workflow that crashes.",
                context=TaskRequestContextCommand(
                    requested_at="2026-05-17T09:30:00+09:00"
                ),
            )
        ).task

        self.assertEqual(snapshot.status, TaskStatus.FAILED)
        self.assertEqual(snapshot.error, "Graph crashed.")
        self.assertIsNone(snapshot.current_action_id)
        self.assertEqual(snapshot.host_actions[0].status, HostActionStatus.FAILED)
        self.assertEqual(len(repository.saved), 1)
        self.assertEqual(repository.saved[0].status, TaskStatus.FAILED)

    def test_append_to_missing_task_raises_not_found(self) -> None:
        repository = FakeTaskRepository()
        use_case = RunTaskUseCase(
            task_repository=repository,
            workflow=FailingWorkflowRuntime(),
        )

        with self.assertRaises(ResourceNotFoundError):
            use_case.execute(
                AppendTaskInputCommand(
                    task_id="55555555-5555-4555-8555-555555555555",
                    request="Follow-up request.",
                    context=TaskRequestContextCommand(
                        requested_at="2026-05-17T09:30:00+09:00"
                    ),
                )
            )

        self.assertEqual(repository.saved, [])


if __name__ == "__main__":
    unittest.main()
