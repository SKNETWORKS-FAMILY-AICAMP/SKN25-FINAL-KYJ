from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.domain.models.workflow.tasks import (
    TaskAnalysis,
    TaskAppendInput,
    TaskContext,
    TaskCreationInput,
    TaskInputEntry,
    TaskInputStatus,
    TaskSnapshot,
    TaskStatus,
)
from foldmind_ai_core.shared.validation import InvalidInputError

ACCEPTED_FOR_PLANNING_MESSAGE = "Task accepted for workflow planning."
NO_ACTIVE_INPUTS_MESSAGE = "Task has no active inputs."
INPUT_REMOVED_REPLANNED_MESSAGE = "Task input removed. Task replanned."


@dataclass(frozen=True, slots=True)
class WorkflowInputQueue:
    def initial_snapshot(
        self,
        task_input: TaskCreationInput,
        *,
        task_id: str,
    ) -> TaskSnapshot:
        return TaskSnapshot(
            task_id=task_id,
            tenant=task_input.tenant,
            request=task_input.request,
            context=task_input.context,
            status=TaskStatus.CLARIFICATION_REQUIRED,
            analysis=TaskAnalysis(message=ACCEPTED_FOR_PLANNING_MESSAGE),
            inputs=[self._entry_from_input(task_input, task_id=task_id, position=0)],
        )

    def append_input(self, snapshot: TaskSnapshot, task_input: TaskAppendInput) -> None:
        inherited_context = self._context_for_append(snapshot, task_input)
        snapshot.inputs.append(
            TaskInputEntry(
                task_input_id=task_input.task_input_id,
                task_id=snapshot.task_id,
                input_text=task_input.request,
                context=inherited_context,
                position=len(snapshot.inputs),
                status=TaskInputStatus.ACTIVE,
            )
        )
        self._prepare_for_planning(
            snapshot,
            message=ACCEPTED_FOR_PLANNING_MESSAGE,
        )

    def remove_input(self, snapshot: TaskSnapshot, task_input_id: str) -> bool:
        for task_input in snapshot.inputs:
            if task_input.task_input_id != task_input_id:
                continue
            if task_input.status == TaskInputStatus.REMOVED:
                return False
            task_input.status = TaskInputStatus.REMOVED
            break
        else:
            raise InvalidInputError(f"Task input not found: {task_input_id}")

        self._prepare_for_planning(
            snapshot,
            message=INPUT_REMOVED_REPLANNED_MESSAGE,
        )
        if snapshot.request:
            return True
        snapshot.analysis = TaskAnalysis(message=NO_ACTIVE_INPUTS_MESSAGE)
        return False

    def _prepare_for_planning(self, snapshot: TaskSnapshot, *, message: str) -> None:
        snapshot.request = self.active_input_text(snapshot.inputs)
        snapshot.context = self.active_context(snapshot.inputs, fallback=snapshot.context)
        snapshot.status = TaskStatus.CLARIFICATION_REQUIRED
        snapshot.analysis = TaskAnalysis(message=message)
        snapshot.current_action_id = None
        snapshot.error = None
        snapshot.result = None
        snapshot.host_actions = []
        snapshot.metadata.pop("workflow_feedback", None)

    @staticmethod
    def active_input_text(inputs: list[TaskInputEntry]) -> str:
        active_inputs = [
            entry.input_text
            for entry in sorted(inputs, key=lambda item: item.position)
            if entry.status == TaskInputStatus.ACTIVE
        ]
        return "\n\n".join(active_inputs)

    @staticmethod
    def active_context(
        inputs: list[TaskInputEntry],
        *,
        fallback: TaskContext,
    ) -> TaskContext:
        active_inputs = [
            entry
            for entry in sorted(inputs, key=lambda item: item.position)
            if entry.status == TaskInputStatus.ACTIVE
        ]
        return active_inputs[-1].context if active_inputs else fallback

    def _context_for_append(
        self,
        snapshot: TaskSnapshot,
        task_input: TaskAppendInput,
    ) -> TaskContext:
        active_context = self.active_context(snapshot.inputs, fallback=snapshot.context)
        return TaskContext(
            requested_at=task_input.context.requested_at,
            document_id=(
                task_input.context.document_id
                if task_input.context.document_id is not None
                else active_context.document_id
            ),
            folder_id=(
                task_input.context.folder_id
                if task_input.context.folder_id is not None
                else active_context.folder_id
            ),
        )

    @staticmethod
    def _entry_from_input(
        task_input: TaskCreationInput | TaskAppendInput,
        *,
        task_id: str,
        position: int,
    ) -> TaskInputEntry:
        return TaskInputEntry(
            task_input_id=task_input.task_input_id,
            task_id=task_id,
            input_text=task_input.request,
            context=task_input.context,
            position=position,
            status=TaskInputStatus.ACTIVE,
        )
