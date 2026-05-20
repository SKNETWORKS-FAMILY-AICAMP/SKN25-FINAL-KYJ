from __future__ import annotations

import unittest

from foldmind_ai_core.core.application.workflows.engine import WorkflowEngine
from foldmind_ai_core.core.application.workflows.host_actions.result_service import (
    HostActionResultService,
)
from foldmind_ai_core.core.application.workflows.plan_compiler import WorkflowPlanCompiler
from foldmind_ai_core.core.application.workflows.state.execution import WorkflowArtifactName
from foldmind_ai_core.core.application.workflows.state.plan import (
    WorkflowAction,
    WorkflowActionType,
    WorkflowPlan,
)
from foldmind_ai_core.core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.core.domain.models.generation.results import GeneratedTextResult
from foldmind_ai_core.core.domain.models.workflow.actions import (
    CreateFolderInput,
    HostAction,
    HostActionType,
)
from foldmind_ai_core.core.domain.models.workflow.tasks import (
    TaskAnalysis,
    TaskContext,
    TaskFinalResult,
    TaskOutputType,
    TaskSnapshot,
    TaskStatus,
)
from foldmind_ai_core.shared.validation import InvalidInputError


class FakePlanningAgent:
    def __init__(self) -> None:
        self.metadata: list[dict[str, object]] = []
        self.context_ids: list[tuple[str | None, str | None]] = []

    def plan(self, query):
        self.metadata.append(dict(query.request_context.metadata))
        self.context_ids.append(
            (query.request_context.document_id, query.request_context.folder_id)
        )
        return WorkflowPlan(
            intent="find_documents",
            actions=[WorkflowAction(action_type=WorkflowActionType.FIND_DOCUMENTS)],
        )


class WorkflowEngineTests(unittest.TestCase):
    def test_engine_rejects_malformed_retry_limit(self) -> None:
        with self.assertRaises(InvalidInputError):
            WorkflowEngine(
                planning=FakePlanningAgent(),
                plan_compiler=WorkflowPlanCompiler(),
                step_executor=object(),
                host_action_results=HostActionResultService(),
                max_tool_retries=True,
            )
        with self.assertRaises(InvalidInputError):
            WorkflowEngine(
                planning=FakePlanningAgent(),
                plan_compiler=WorkflowPlanCompiler(),
                step_executor=object(),
                host_action_results=HostActionResultService(),
                max_tool_retries=-1,
            )

    def test_replan_clears_stale_host_action_state(self) -> None:
        stale_action = HostAction(
            action_type=HostActionType.CREATE_FOLDER,
            summary="Create stale folder.",
            input=CreateFolderInput(name="Old"),
            action_id="action-1",
        )
        state = WorkflowState(
            task=TaskSnapshot(
                task_id="task-1",
                tenant="tenant-1",
                request="Find documents.",
                context=TaskContext(
                    requested_at="2026-05-17T09:30:00+09:00",
                    document_id="doc-context",
                    folder_id="folder-context",
                ),
                status=TaskStatus.CLARIFICATION_REQUIRED,
                analysis=TaskAnalysis(message="Needs replan."),
                result=TaskFinalResult(
                    result_type=TaskOutputType.SUMMARY,
                    result=GeneratedTextResult(text="Stale summary."),
                ),
                error="Previous failure.",
                host_actions=[stale_action],
                current_action_id="action-1",
                metadata={
                    "workflow_feedback": "Use the revised request.",
                    "document": {"document_id": "doc-1"},
                },
            ),
            pending_actions=[stale_action],
            needs_replan=True,
            retry_action_id="action-1",
            failed_step_key="0:0:plan_host_actions",
            last_error="stale failure",
            retry_counts={"0:0:plan_host_actions": 1},
        )
        state.artifacts.write(WorkflowArtifactName.SUMMARY, GeneratedTextResult(text="Stale."))
        planning_agent = FakePlanningAgent()
        engine = WorkflowEngine(
            planning=planning_agent,
            plan_compiler=WorkflowPlanCompiler(),
            step_executor=object(),
            host_action_results=HostActionResultService(),
        )

        engine.replan(state)

        self.assertFalse(state.needs_replan)
        self.assertIsNone(state.retry_action_id)
        self.assertIsNone(state.failed_step_key)
        self.assertIsNone(state.last_error)
        self.assertEqual(state.pending_actions, [])
        self.assertEqual(state.retry_counts, {})
        self.assertEqual(state.artifacts.items, {})
        self.assertEqual(state.task.host_actions, [])
        self.assertIsNone(state.task.current_action_id)
        self.assertIsNone(state.task.error)
        self.assertEqual(state.task.status, TaskStatus.CLARIFICATION_REQUIRED)
        self.assertIsNone(state.task.result)
        self.assertEqual(state.task.analysis.message, "Task replanned.")
        self.assertEqual(
            planning_agent.metadata,
            [
                {
                    "workflow_feedback": "Use the revised request.",
                    "document": {"document_id": "doc-1"},
                }
            ],
        )
        self.assertEqual(state.task.metadata, {"document": {"document_id": "doc-1"}})
        self.assertEqual(
            state.query.request_context.metadata,
            {"document": {"document_id": "doc-1"}},
        )
        self.assertEqual(planning_agent.context_ids, [("doc-context", "folder-context")])

    def test_fail_clears_pending_host_action_state(self) -> None:
        pending_action = HostAction(
            action_type=HostActionType.CREATE_FOLDER,
            summary="Create folder.",
            input=CreateFolderInput(name="Plans"),
            action_id="action-1",
        )
        state = WorkflowState(
            task=TaskSnapshot(
                task_id="task-1",
                tenant="tenant-1",
                request="Find documents.",
                context=TaskContext(requested_at="2026-05-17T09:30:00+09:00"),
                status=TaskStatus.CLARIFICATION_REQUIRED,
                analysis=TaskAnalysis(message="Running."),
                current_action_id="action-1",
            ),
            pending_actions=[pending_action],
            last_error="step failed",
            needs_replan=True,
            retry_action_id="action-1",
        )
        engine = WorkflowEngine(
            planning=FakePlanningAgent(),
            plan_compiler=WorkflowPlanCompiler(),
            step_executor=object(),
            host_action_results=HostActionResultService(),
        )

        engine.fail(state)

        self.assertEqual(state.task.status, TaskStatus.FAILED)
        self.assertEqual(state.task.error, "step failed")
        self.assertEqual(state.pending_actions, [])
        self.assertIsNone(state.task.current_action_id)
        self.assertFalse(state.needs_replan)
        self.assertIsNone(state.retry_action_id)


if __name__ == "__main__":
    unittest.main()
