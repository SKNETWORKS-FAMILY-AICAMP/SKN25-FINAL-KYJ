from __future__ import annotations

from typing import TYPE_CHECKING

from foldmind_ai_core.application.workflows.state.execution import (
    StepOutcome,
    WorkflowArtifactName,
)
from foldmind_ai_core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.application.workflows.steps.options import requested_host_actions
from foldmind_ai_core.domain.retrieval.queries import AIQuery
from foldmind_ai_core.domain.workflow.actions import ActionPlan
from foldmind_ai_core.shared.types import Metadata

if TYPE_CHECKING:
    from foldmind_ai_core.application.workflows.steps.executor import WorkflowStepExecutor


def plan_host_actions(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: AIQuery,
    options: Metadata,
) -> StepOutcome:
    plan = ctx.host_action_builder.build(
        task=state.task,
        round_index=state.plan.round_index if state.plan is not None else 0,
        draft=ctx.artifacts.draft(state),
        summary=ctx.artifacts.summary(state),
        synthesized_report=ctx.artifacts.synthesized_report(state),
        folder_recommendation=ctx.artifacts.folder_recommendation(state),
        related_recommendation=ctx.artifacts.related_recommendation(state),
        requested_actions=requested_host_actions(options),
        options=options,
    )
    ctx.host_action_results.merge_host_actions(state, plan.host_actions)
    result = ActionPlan(
        summary=plan.summary,
        steps=plan.steps,
        host_actions=list(state.task.host_actions),
    )
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.ACTION_PLAN: result,
        },
        output=result,
    )
