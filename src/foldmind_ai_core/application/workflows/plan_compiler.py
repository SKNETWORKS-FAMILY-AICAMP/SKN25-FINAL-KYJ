from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.workflows.state.execution import (
    WorkflowExecutionPlan,
    WorkflowStep,
    WorkflowStepInput,
)
from foldmind_ai_core.application.workflows.state.plan import (
    WorkflowAction,
    WorkflowActionType,
    WorkflowPlan,
)


@dataclass(slots=True)
class WorkflowPlanCompiler:
    def compile(self, workflow_plan: WorkflowPlan) -> WorkflowExecutionPlan:
        return WorkflowExecutionPlan(
            steps=[
                self._step_from_workflow_action(
                    action,
                    plan_requires_confirmation=workflow_plan.requires_confirmation,
                )
                for action in workflow_plan.actions
            ]
        )

    def _step_from_workflow_action(
        self,
        action: WorkflowAction,
        *,
        plan_requires_confirmation: bool = False,
    ) -> WorkflowStep:
        options = dict(action.params)
        if action.action_type == WorkflowActionType.PLAN_HOST_ACTIONS and (
            action.requires_confirmation or plan_requires_confirmation
        ):
            options["requires_confirmation"] = True
        return WorkflowStep(
            action_type=action.action_type,
            reason=action.reason,
            step_input=WorkflowStepInput(options=options),
        )
