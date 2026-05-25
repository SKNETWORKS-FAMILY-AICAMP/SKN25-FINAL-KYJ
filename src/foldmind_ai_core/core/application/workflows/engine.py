from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from foldmind_ai_core.core.application.models.search import RequestContext
from foldmind_ai_core.core.application.models.retrieval import RetrievalQuery
from foldmind_ai_core.core.application.workflows.host_actions.result_service import (
    HostActionResultService,
)
from foldmind_ai_core.core.application.workflows.plan_compiler import WorkflowPlanCompiler
from foldmind_ai_core.core.application.workflows.state.execution import WorkflowArtifacts
from foldmind_ai_core.core.application.workflows.state.plan import (
    WorkflowActionType,
    WorkflowPlan,
)
from foldmind_ai_core.core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.core.application.workflows.steps.executor import WorkflowStepExecutor
from foldmind_ai_core.core.domain.models.host_actions import HostActionResult
from foldmind_ai_core.core.domain.models.tasks import (
    TaskAnalysis,
    TaskJob,
    TaskJobStatus,
    TaskStatus,
)
from foldmind_ai_core.shared.types import JsonObject
from foldmind_ai_core.shared.validation import InvalidInputError


class WorkflowPlanner(Protocol):
    async def plan(self, query: RetrievalQuery) -> WorkflowPlan:
        ...


@dataclass(slots=True)
class WorkflowEngine:
    planning: WorkflowPlanner
    plan_compiler: WorkflowPlanCompiler
    step_executor: WorkflowStepExecutor
    host_action_results: HostActionResultService
    max_tool_retries: int = 1

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_tool_retries, bool)
            or not isinstance(self.max_tool_retries, int)
            or self.max_tool_retries < 0
        ):
            raise InvalidInputError("max_tool_retries must be a non-negative integer.")

    async def prepare(self, state: WorkflowState) -> WorkflowState:
        round_index = state.trace.rounds
        query = RetrievalQuery(
            text=state.task.request,
            request_context=RequestContext(
                tenant=state.task.tenant,
                requested_at=state.task.context.requested_at,
                document_id=state.task.context.document_id,
                folder_id=state.task.context.folder_id,
                metadata=dict(state.task.metadata),
            ),
        )
        workflow_plan = await self.planning.plan(query)
        execution_plan = self.plan_compiler.compile(workflow_plan, query=query)
        execution_plan.round_index = round_index
        state.query = query
        state.plan = execution_plan
        state.next_step_index = 0
        state.trace.rounds += 1
        state.trace.replans.append(execution_plan)
        state.task.jobs.extend(
            TaskJob(
                job_type=str(step.action_type),
                round_index=round_index,
                position=position,
                reason=step.reason,
                input=_job_input(step),
            )
            for position, step in enumerate(execution_plan.steps)
        )
        return state

    async def replan(self, state: WorkflowState) -> WorkflowState:
        state.needs_replan = False
        state.retry_action_id = None
        state.failed_step_key = None
        state.last_error = None
        state.pending_actions = []
        state.retry_counts = {}
        state.artifacts = WorkflowArtifacts()
        state.task.host_actions = []
        state.task.current_action_id = None
        state.task.error = None
        state.task.result = None
        state.task.status = TaskStatus.CLARIFICATION_REQUIRED
        state.task.analysis = TaskAnalysis(message="Task replanned.")
        state = await self.prepare(state)
        state.task.metadata.pop("workflow_feedback", None)
        if state.query is not None:
            state.query.request_context.metadata.pop("workflow_feedback", None)
        return state

    def retry_host_action(self, state: WorkflowState) -> WorkflowState:
        return self.host_action_results.retry_host_action(state)

    def fail(self, state: WorkflowState) -> WorkflowState:
        state.task.status = TaskStatus.FAILED
        state.task.error = state.last_error or "Workflow failed."
        state.task.analysis.message = "Task failed."
        state.pending_actions = []
        state.task.current_action_id = None
        state.needs_replan = False
        state.retry_action_id = None
        return state

    def has_next_step(self, state: WorkflowState) -> bool:
        return state.plan is not None and state.next_step_index < len(state.plan.steps)

    async def run_step(
        self,
        state: WorkflowState,
        *,
        expected_action_type: WorkflowActionType | None,
    ) -> WorkflowState:
        if state.query is None:
            raise RuntimeError("Workflow query is not prepared.")
        if state.plan is None:
            raise RuntimeError("Workflow plan is not prepared.")
        if not self.has_next_step(state):
            return state

        step = state.plan.steps[state.next_step_index]
        if expected_action_type is not None and step.action_type != expected_action_type:
            raise RuntimeError(
                f"Expected workflow action {expected_action_type}, got {step.action_type}."
            )
        step_query = step.step_input.query or state.query
        job = _job_for_step(
            state,
            round_index=state.plan.round_index,
            position=state.next_step_index,
            action_type=step.action_type,
            reason=step.reason,
            input_json=_job_input(step),
        )
        job.status = TaskJobStatus.RUNNING
        job.started_at = job.started_at or _utc_timestamp()
        job.finished_at = None
        job.error = None

        try:
            await self.step_executor.execute(
                state,
                step.action_type,
                step_query,
                step.step_input.options,
                job,
            )
        except Exception as exc:
            job.status = TaskJobStatus.FAILED
            job.error = str(exc)
            job.finished_at = _utc_timestamp()
            raise

        job.status = TaskJobStatus.SUCCEEDED
        job.finished_at = _utc_timestamp()
        state.next_step_index += 1
        return state

    def can_retry_step(self, state: WorkflowState) -> bool:
        if state.failed_step_key is None:
            return False
        return state.retry_counts.get(state.failed_step_key, 0) <= self.max_tool_retries

    def apply_action_result(
        self,
        state: WorkflowState,
        result: HostActionResult,
    ) -> WorkflowState:
        return self.host_action_results.apply(state, result)

    def current_step_key(self, state: WorkflowState) -> str:
        if state.plan is None or state.next_step_index >= len(state.plan.steps):
            return "unknown"
        step = state.plan.steps[state.next_step_index]
        return f"{state.plan.round_index}:{state.next_step_index}:{step.action_type}"


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _job_input(step: object) -> JsonObject:
    from foldmind_ai_core.core.application.workflows.state.execution import WorkflowStep

    if not isinstance(step, WorkflowStep):
        return {}
    return {
        "artifact_refs": [artifact.value for artifact in step.step_input.artifact_refs],
        "options": dict(step.step_input.options),
    }


def _job_for_step(
    state: WorkflowState,
    *,
    round_index: int,
    position: int,
    action_type: WorkflowActionType,
    reason: str,
    input_json: JsonObject,
) -> TaskJob:
    for job in state.task.jobs:
        if job.round_index == round_index and job.position == position:
            return job
    job = TaskJob(
        job_type=str(action_type),
        round_index=round_index,
        position=position,
        reason=reason,
        input=input_json,
    )
    state.task.jobs.append(job)
    return job
