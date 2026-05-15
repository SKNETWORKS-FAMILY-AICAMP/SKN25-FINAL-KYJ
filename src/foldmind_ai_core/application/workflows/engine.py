from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.agents.planning_agent import PlanningAgent
from foldmind_ai_core.application.workflows.host_actions.result_handler import (
    HostActionResultHandler,
)
from foldmind_ai_core.application.workflows.plan_compiler import WorkflowPlanCompiler
from foldmind_ai_core.application.workflows.state.execution import (
    WorkflowStepExecution,
    WorkflowStepStatus,
)
from foldmind_ai_core.application.workflows.state.plan import WorkflowActionType
from foldmind_ai_core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.application.workflows.steps.executor import WorkflowStepExecutor
from foldmind_ai_core.domain.retrieval.queries import AIQuery, RequestContext
from foldmind_ai_core.domain.workflow.actions import HostActionResult
from foldmind_ai_core.domain.workflow.tasks import TaskStatus


@dataclass(slots=True)
class WorkflowEngine:
    planning_agent: PlanningAgent
    plan_compiler: WorkflowPlanCompiler
    step_executor: WorkflowStepExecutor
    host_action_results: HostActionResultHandler
    max_tool_retries: int = 1

    def prepare(self, state: WorkflowState) -> WorkflowState:
        round_index = state.trace.rounds
        query = AIQuery(
            text=state.task.request,
            request_context=RequestContext(
                tenant=state.task.tenant,
                metadata=dict(state.task.metadata),
            ),
        )
        workflow_plan = self.planning_agent.plan(query)
        execution_plan = self.plan_compiler.compile(workflow_plan)
        execution_plan.round_index = round_index
        state.query = query
        state.plan = execution_plan
        state.next_step_index = 0
        state.trace.rounds += 1
        state.trace.replans.append(execution_plan)
        return state

    def replan(self, state: WorkflowState) -> WorkflowState:
        state.needs_replan = False
        state.retry_action_id = None
        state.failed_step_key = None
        state.last_error = None
        state.pending_actions = []
        state = self.prepare(state)
        state.task.analysis.message = "Task replanned."
        return state

    def retry_host_action(self, state: WorkflowState) -> WorkflowState:
        return self.host_action_results.retry_host_action(state)

    def fail(self, state: WorkflowState) -> WorkflowState:
        state.task.status = TaskStatus.FAILED
        state.task.error = state.last_error or "Workflow failed."
        state.task.analysis.message = "Task failed."
        state.needs_replan = False
        state.retry_action_id = None
        return state

    def has_next_step(self, state: WorkflowState) -> bool:
        return state.plan is not None and state.next_step_index < len(state.plan.steps)

    def run_step(
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
        execution = WorkflowStepExecution(
            step=step,
            round_index=state.plan.round_index,
            status=WorkflowStepStatus.RUNNING,
            resolved_query=step_query,
            artifacts_read=step.step_input.artifact_refs,
        )
        state.trace.steps.append(execution)

        try:
            self.step_executor.execute(
                state,
                step.action_type,
                step_query,
                step.step_input.options,
                execution,
            )
        except Exception as exc:
            execution.status = WorkflowStepStatus.FAILED
            execution.error = str(exc)
            raise

        execution.status = WorkflowStepStatus.SUCCEEDED
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
