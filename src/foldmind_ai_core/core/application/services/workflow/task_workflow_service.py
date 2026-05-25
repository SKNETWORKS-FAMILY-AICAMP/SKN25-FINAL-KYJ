from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

from foldmind_ai_core.core.application.models.task_commands import (
    AppendTaskInputCommand,
    CreateTaskCommand,
    GetTaskQuery,
    RecordActionResultCommand,
    RemoveTaskInputCommand,
)
from foldmind_ai_core.core.application.errors import (
    ConcurrentTaskUpdateError,
    ResourceNotFoundError,
)
from foldmind_ai_core.core.application.ports.outbound.runtime.workflow_runtime import (
    WorkflowRuntime,
)
from foldmind_ai_core.core.application.ports.outbound.session.task_session import (
    TaskSessionProvider,
)
from foldmind_ai_core.core.application.models.task_results import (
    RecordActionResult,
)
from foldmind_ai_core.core.domain.models.tasks import TaskSnapshot
from foldmind_ai_core.core.domain.services.workflow_domain_service import WorkflowDomainService
from foldmind_ai_core.core.domain.services.workflow_input_service import WorkflowInputService
from foldmind_ai_core.shared.internal_ids import new_internal_id


@dataclass(slots=True)
class TaskWorkflowService:
    tasks: TaskSessionProvider
    workflow: WorkflowRuntime
    input_queue: WorkflowInputService = field(default_factory=WorkflowInputService)
    workflow_rules: WorkflowDomainService = field(default_factory=WorkflowDomainService)

    async def create_task(self, command: CreateTaskCommand) -> TaskSnapshot:
        snapshot = self.input_queue.initial_snapshot(
            task_id=new_internal_id(),
            tenant=command.tenant,
            request=command.request,
            context=command.context,
            task_input_id=new_internal_id(),
        )
        async with self.tasks.transaction() as session:
            snapshot = await session.tasks.create(snapshot)
        return await self._run_and_save(
            snapshot,
            expected_snapshot=deepcopy(snapshot),
        )

    async def append_task_input(self, command: AppendTaskInputCommand) -> TaskSnapshot:
        async with self.tasks.session() as session:
            snapshot = await session.tasks.get(task_id=command.task_id)
        if snapshot is None:
            raise ResourceNotFoundError(f"Task not found: {command.task_id}")

        expected_snapshot = deepcopy(snapshot)
        self.input_queue.append_input(
            snapshot,
            request=command.request,
            context=command.context,
            task_input_id=new_internal_id(),
        )
        return await self._run_and_save(
            snapshot,
            expected_snapshot=expected_snapshot,
        )

    async def get_task(self, query: GetTaskQuery) -> TaskSnapshot:
        async with self.tasks.session() as session:
            snapshot = await session.tasks.get(task_id=query.task_id)
        if snapshot is None:
            raise ResourceNotFoundError(f"Task not found: {query.task_id}")
        return snapshot

    async def remove_task_input(
        self,
        command: RemoveTaskInputCommand,
    ) -> TaskSnapshot:
        async with self.tasks.session() as session:
            snapshot = await session.tasks.get_by_input_id(
                task_input_id=command.task_input_id
            )
        if snapshot is None:
            raise ResourceNotFoundError(f"Task input not found: {command.task_input_id}")
        expected_snapshot = deepcopy(snapshot)

        should_replan = self.input_queue.remove_input(
            snapshot,
            command.task_input_id,
        )
        if not should_replan:
            await self._save_snapshot(
                snapshot,
                expected_snapshot=expected_snapshot,
                conflict_message=(
                    f"Task changed while input was being removed: {snapshot.task_id}"
                ),
            )
            return snapshot

        return await self._run_and_save(
            snapshot,
            expected_snapshot=expected_snapshot,
        )

    async def record_action_result(
        self,
        command: RecordActionResultCommand,
    ) -> RecordActionResult:
        result = command.result
        async with self.tasks.session() as session:
            current_snapshot = await session.tasks.get_by_action_id(
                action_id=result.action_id
            )
        if current_snapshot is None:
            raise ResourceNotFoundError(f"Host action not found: {result.action_id}")
        expected_snapshot = deepcopy(current_snapshot)
        current_action = next(
            (
                action
                for action in current_snapshot.host_actions
                if action.action_id == result.action_id
            ),
            None,
        )
        if current_action is None:
            raise ResourceNotFoundError(f"Host action not found: {result.action_id}")
        self.workflow_rules.validate_host_action_result(current_action, result)

        snapshot = await self.workflow.resume_from_action_result(
            task_id=current_snapshot.task_id,
            result=result,
        )
        await self._save_snapshot(
            snapshot,
            expected_snapshot=expected_snapshot,
            conflict_message=(
                f"Task changed while action result was being recorded: {snapshot.task_id}"
            ),
        )
        return RecordActionResult(recorded=True, task=snapshot)

    async def _run_and_save(
        self,
        snapshot: TaskSnapshot,
        *,
        expected_snapshot: TaskSnapshot,
    ) -> TaskSnapshot:
        try:
            snapshot = await self.workflow.run(snapshot)
            self.workflow_rules.mark_result(snapshot)
        except Exception as exc:
            self.workflow_rules.mark_failed(snapshot, exc)

        await self._save_snapshot(
            snapshot,
            expected_snapshot=expected_snapshot,
            conflict_message=f"Task changed while workflow was running: {snapshot.task_id}",
        )
        return snapshot

    async def _save_snapshot(
        self,
        snapshot: TaskSnapshot,
        *,
        expected_snapshot: TaskSnapshot,
        conflict_message: str,
    ) -> None:
        async with self.tasks.transaction() as session:
            saved = await session.tasks.save_if_unchanged(
                snapshot,
                expected_snapshot=expected_snapshot,
            )
        if not saved:
            raise ConcurrentTaskUpdateError(conflict_message)
