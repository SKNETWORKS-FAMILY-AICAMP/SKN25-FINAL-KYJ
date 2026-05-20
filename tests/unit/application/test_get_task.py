from __future__ import annotations

import unittest

from foldmind_ai_core.core.application.commands.workflow import GetTaskQuery
from foldmind_ai_core.core.application.errors import ResourceNotFoundError
from foldmind_ai_core.core.application.use_cases.workflow.get_task import GetTaskUseCase
from foldmind_ai_core.core.domain.models.workflow.tasks import TaskSnapshot


class FakeTaskRepository:
    def get(self, *, task_id: str) -> TaskSnapshot | None:
        return None

    def get_by_input_id(self, *, task_input_id: str) -> TaskSnapshot | None:
        return None

    def get_by_action_id(self, *, action_id: str) -> TaskSnapshot | None:
        return None

    def create(self, snapshot: TaskSnapshot) -> None:
        return None

    def save(self, snapshot: TaskSnapshot) -> None:
        return None


class GetTaskUseCaseTests(unittest.TestCase):
    def test_get_task_raises_when_task_is_missing(self) -> None:
        with self.assertRaises(ResourceNotFoundError):
            GetTaskUseCase(task_repository=FakeTaskRepository()).execute(
                GetTaskQuery(
                    task_id="55555555-5555-4555-8555-555555555555",
                )
            )


if __name__ == "__main__":
    unittest.main()
