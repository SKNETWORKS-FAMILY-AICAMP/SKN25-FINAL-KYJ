from __future__ import annotations

import unittest
from contextlib import asynccontextmanager

from foldmind_ai_core.core.application.models.task_commands import GetTaskQuery
from foldmind_ai_core.core.application.errors import ResourceNotFoundError
from foldmind_ai_core.core.application.services.workflow.task_workflow_service import (
    TaskWorkflowService,
)
from foldmind_ai_core.core.domain.models.host_actions import HostActionResult
from foldmind_ai_core.core.domain.models.tasks import TaskSnapshot


class FakeTaskRepository:
    async def get(self, *, task_id: str) -> TaskSnapshot | None:
        return None

    async def create(self, snapshot: TaskSnapshot) -> TaskSnapshot:
        return snapshot

    async def save_if_unchanged(
        self,
        snapshot: TaskSnapshot,
        *,
        expected_snapshot: TaskSnapshot,
    ) -> bool:
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
    async def run(self, snapshot: TaskSnapshot) -> TaskSnapshot:
        return snapshot

    async def resume_from_action_result(
        self,
        *,
        task_id: str,
        result: HostActionResult,
    ) -> TaskSnapshot:
        raise AssertionError("resume_from_action_result should not be called")


class GetTaskServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_task_raises_when_task_is_missing(self) -> None:
        with self.assertRaises(ResourceNotFoundError):
            await TaskWorkflowService(
                tasks=FakeTaskSessionProvider(FakeTaskRepository()),
                workflow=FakeWorkflowRuntime(),
            ).get_task(
                GetTaskQuery(
                    task_id="55555555-5555-4555-8555-555555555555",
                )
            )


if __name__ == "__main__":
    unittest.main()
