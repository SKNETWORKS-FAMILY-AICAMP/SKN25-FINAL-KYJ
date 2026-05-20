from __future__ import annotations

import unittest

from langgraph.graph import END

from foldmind_ai_core.adapters.outbound.workflow_runtime.checkpoint_codec import (
    workflow_state_to_checkpoint,
)
from foldmind_ai_core.adapters.outbound.workflow_runtime.nodes import LangGraphWorkflowNodes
from foldmind_ai_core.core.application.workflows.state.execution import (
    WorkflowExecutionPlan,
    WorkflowStep,
)
from foldmind_ai_core.core.application.workflows.state.plan import WorkflowActionType
from foldmind_ai_core.core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.core.domain.models.workflow.tasks import TaskAnalysis, TaskContext, TaskSnapshot, TaskStatus


class LangGraphWorkflowNodesTests(unittest.TestCase):
    def test_terminal_task_stops_after_action_result_with_remaining_steps(self) -> None:
        nodes = LangGraphWorkflowNodes(engine=object())
        state = _checkpoint_for_terminal_task(TaskStatus.REJECTED)

        route = nodes.route_after_resume(state)

        self.assertEqual(route, END)

    def test_terminal_task_stops_after_step_with_remaining_steps(self) -> None:
        nodes = LangGraphWorkflowNodes(engine=object())
        state = _checkpoint_for_terminal_task(TaskStatus.FAILED)

        route = nodes.route_after_step(state)

        self.assertEqual(route, END)


def _checkpoint_for_terminal_task(status: TaskStatus):
    return workflow_state_to_checkpoint(
        WorkflowState(
            task=TaskSnapshot(
                task_id="task-1",
                tenant="tenant-1",
                request="Run task.",
                context=TaskContext(requested_at="2026-05-17T09:30:00+09:00"),
                status=status,
                analysis=TaskAnalysis(message="Terminal."),
            ),
            plan=WorkflowExecutionPlan(
                steps=[
                    WorkflowStep(
                        action_type=WorkflowActionType.FIND_DOCUMENTS,
                        reason="Remaining step.",
                    )
                ],
            ),
            next_step_index=0,
        )
    )


if __name__ == "__main__":
    unittest.main()
