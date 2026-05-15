from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.domain.workflow.actions import HostActionResult
from foldmind_ai_core.domain.workflow.tasks import (
    TaskAppendRequest,
    TaskCreationRequest,
    TaskSnapshot,
)


class RunTaskUseCasePort(Protocol):
    def execute(self, request: TaskCreationRequest | TaskAppendRequest) -> TaskSnapshot:
        ...


class GetTaskUseCasePort(Protocol):
    def execute(self, *, task_id: str) -> TaskSnapshot:
        ...


class RemoveTaskRequestUseCasePort(Protocol):
    def execute(
        self,
        *,
        task_request_id: str,
    ) -> TaskSnapshot:
        ...


class RecordActionResultUseCasePort(Protocol):
    def execute(self, *, result: HostActionResult) -> TaskSnapshot:
        ...
