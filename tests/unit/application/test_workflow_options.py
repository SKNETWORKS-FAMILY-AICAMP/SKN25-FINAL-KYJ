from __future__ import annotations

import unittest
from datetime import datetime

from foldmind_ai_core.core.application.models.search import RequestContext
from foldmind_ai_core.core.application.models.retrieval import RetrievalQuery
from foldmind_ai_core.core.application.workflows.option_values import (
    bool_option,
    instruction_option,
    string_tuple,
)
from foldmind_ai_core.core.application.workflows.plan_compiler import WorkflowPlanCompiler
from foldmind_ai_core.core.application.workflows.plan_factory import (
    workflow_plan_from_mapping,
)
from foldmind_ai_core.core.application.workflows.state.plan import (
    WorkflowAction,
    WorkflowActionType,
    WorkflowPlan,
    WorkflowRiskLevel,
)
from foldmind_ai_core.core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.core.application.workflows.steps.options import (
    document_from_task,
    requested_host_actions,
)
from foldmind_ai_core.core.domain.models.host_actions import HostActionType
from foldmind_ai_core.core.domain.models.tasks import (
    TaskAnalysis,
    TaskContext,
    TaskSnapshot,
    TaskStatus,
)


class WorkflowOptionTests(unittest.TestCase):
    def test_bool_option_accepts_only_boolean_values(self) -> None:
        self.assertFalse(bool_option({}, "enabled"))
        self.assertTrue(bool_option({"enabled": True}, "enabled"))
        self.assertFalse(bool_option({"enabled": False}, "enabled"))

        with self.assertRaises(TypeError):
            bool_option({"enabled": "false"}, "enabled")
        with self.assertRaises(TypeError):
            bool_option({"enabled": 1}, "enabled")

    def test_instruction_option_requires_non_blank_string(self) -> None:
        self.assertEqual(
            instruction_option({"instruction": " Summarize this. "}), "Summarize this."
        )

        with self.assertRaises(ValueError):
            instruction_option({})
        with self.assertRaises(ValueError):
            instruction_option({"instruction": " "})
        with self.assertRaises(TypeError):
            instruction_option({"instruction": ["Summarize this."]})

    def test_workflow_action_params_reject_non_finite_floats(self) -> None:
        with self.assertRaises(ValueError):
            WorkflowAction(
                action_type=WorkflowActionType.FIND_DOCUMENTS,
                params={"score": float("nan")},
            )
        with self.assertRaises(ValueError):
            WorkflowAction(
                action_type=WorkflowActionType.FIND_DOCUMENTS,
                params={"score": float("inf")},
            )

    def test_workflow_plan_normalizes_llm_boundary_enums(self) -> None:
        plan = workflow_plan_from_mapping(
            {
                "intent": " answer ",
                "risk_level": " low ",
                "actions": [{"type": " find_documents "}],
            }
        )

        self.assertEqual(plan.intent, "answer")
        self.assertEqual(plan.risk_level, WorkflowRiskLevel.LOW)
        self.assertEqual(plan.actions[0].action_type, WorkflowActionType.FIND_DOCUMENTS)

        with self.assertRaises(ValueError):
            workflow_plan_from_mapping(
                {
                    "intent": " ",
                    "actions": [{"type": "find_documents"}],
                }
            )

    def test_workflow_plan_requires_instruction_for_generation_actions(self) -> None:
        generation_actions = (
            "answer_question",
            "summarize_documents",
            "generate_draft",
            "explore_ideas",
            "analyze_documents",
        )

        for action_type in generation_actions:
            with self.subTest(action_type=action_type):
                with self.assertRaises(ValueError):
                    workflow_plan_from_mapping(
                        {
                            "intent": "generation",
                            "actions": [{"type": action_type}],
                        }
                    )
                with self.assertRaises(ValueError):
                    workflow_plan_from_mapping(
                        {
                            "intent": "generation",
                            "actions": [
                                {
                                    "type": action_type,
                                    "params": {"instruction": " "},
                                }
                            ],
                        }
                    )
                with self.assertRaises(TypeError):
                    workflow_plan_from_mapping(
                        {
                            "intent": "generation",
                            "actions": [
                                {
                                    "type": action_type,
                                    "params": {"instruction": ["not a string"]},
                                }
                            ],
                        }
                    )

                actions = (
                    [
                        {"type": "find_documents"},
                        {"type": "classify_documents"},
                        {
                            "type": action_type,
                            "params": {"instruction": " Do the action. "},
                        },
                    ]
                    if action_type == "analyze_documents"
                    else [
                        {"type": "find_documents"},
                        {
                            "type": action_type,
                            "params": {"instruction": " Do the action. "},
                        },
                    ]
                )
                plan = workflow_plan_from_mapping(
                    {
                        "intent": "generation",
                        "actions": actions,
                    }
                )
                self.assertEqual(plan.actions[-1].params["instruction"], "Do the action.")

    def test_workflow_plan_does_not_require_instruction_for_non_generation_actions(self) -> None:
        plan = workflow_plan_from_mapping(
            {
                "intent": "find",
                "actions": [
                    {"type": "find_documents"},
                    {"type": "present_documents"},
                    {"type": "find_folders"},
                    {"type": "plan_host_actions"},
                ],
            }
        )

        self.assertEqual(
            [action.action_type for action in plan.actions],
            [
                WorkflowActionType.FIND_DOCUMENTS,
                WorkflowActionType.PRESENT_DOCUMENTS,
                WorkflowActionType.FIND_FOLDERS,
                WorkflowActionType.PLAN_HOST_ACTIONS,
            ],
        )

    def test_plan_compiler_maps_temporal_params_to_query_scope(self) -> None:
        plan = WorkflowPlan(
            intent="find",
            actions=[
                WorkflowAction(
                    action_type=WorkflowActionType.FIND_DOCUMENTS,
                    params={
                        "temporal": {
                            "field": "created_at",
                            "sort": "desc",
                            "period": "yesterday",
                        }
                    },
                )
            ],
        )
        query = RetrievalQuery(
            text="지난번에 작성한 회의록",
            request_context=RequestContext(
                tenant="tenant-1",
                requested_at="2026-05-17T09:30:00+09:00",
            ),
        )

        execution_plan = WorkflowPlanCompiler().compile(plan, query=query)

        step_query = execution_plan.steps[0].step_input.query
        self.assertIsNotNone(step_query)
        assert step_query is not None
        self.assertIsNotNone(step_query.scope)
        assert step_query.scope is not None
        self.assertEqual(
            step_query.scope.created_at,
            datetime.fromisoformat("2026-05-16T00:00:00+09:00"),
        )
        self.assertEqual(step_query.scope.sort.field, "created_at")
        self.assertEqual(step_query.scope.sort.direction, "desc")

    def test_plan_compiler_maps_current_document_context_to_query_scope(self) -> None:
        plan = WorkflowPlan(
            intent="summarize",
            source_scope="current_document",
            actions=[
                WorkflowAction(action_type=WorkflowActionType.FIND_DOCUMENTS),
                WorkflowAction(
                    action_type=WorkflowActionType.SUMMARIZE_DOCUMENTS,
                    params={"instruction": "Summarize the current document."},
                ),
            ],
        )
        query = RetrievalQuery(
            text="이 문서 요약해줘",
            request_context=RequestContext(
                tenant="tenant-1",
                requested_at="2026-05-17T09:30:00+09:00",
                document_id="doc-context",
            ),
        )

        execution_plan = WorkflowPlanCompiler().compile(plan, query=query)

        step_query = execution_plan.steps[0].step_input.query
        self.assertIsNotNone(step_query)
        assert step_query is not None
        self.assertIsNotNone(step_query.scope)
        assert step_query.scope is not None
        self.assertEqual(step_query.scope.document_id, "doc-context")

    def test_plan_compiler_maps_current_folder_context_to_query_scope(self) -> None:
        plan = WorkflowPlan(
            intent="summarize",
            source_scope="current_folder",
            actions=[WorkflowAction(action_type=WorkflowActionType.FIND_DOCUMENTS)],
        )
        query = RetrievalQuery(
            text="이 폴더 문서 요약해줘",
            request_context=RequestContext(
                tenant="tenant-1",
                requested_at="2026-05-17T09:30:00+09:00",
                folder_id="folder-context",
            ),
        )

        execution_plan = WorkflowPlanCompiler().compile(plan, query=query)

        step_query = execution_plan.steps[0].step_input.query
        self.assertIsNotNone(step_query)
        assert step_query is not None
        self.assertIsNotNone(step_query.scope)
        assert step_query.scope is not None
        self.assertEqual(step_query.scope.folder_ids, ("folder-context",))

    def test_plan_compiler_converts_missing_current_context_to_clarification(self) -> None:
        plan = WorkflowPlan(
            intent="summarize",
            source_scope="current_document",
            actions=[WorkflowAction(action_type=WorkflowActionType.FIND_DOCUMENTS)],
        )
        query = RetrievalQuery(
            text="이 문서 요약해줘",
            request_context=RequestContext(
                tenant="tenant-1",
                requested_at="2026-05-17T09:30:00+09:00",
            ),
        )

        execution_plan = WorkflowPlanCompiler().compile(plan, query=query)

        self.assertEqual(len(execution_plan.steps), 1)
        self.assertEqual(
            execution_plan.steps[0].action_type,
            WorkflowActionType.REQUEST_CLARIFICATION,
        )
        self.assertIn("question", execution_plan.steps[0].step_input.options)

    def test_plan_compiler_adds_present_documents_for_plain_document_search(self) -> None:
        plan = WorkflowPlan(
            intent="find",
            actions=[WorkflowAction(action_type=WorkflowActionType.FIND_DOCUMENTS)],
        )

        execution_plan = WorkflowPlanCompiler().compile(plan)

        self.assertEqual(
            [step.action_type for step in execution_plan.steps],
            [
                WorkflowActionType.FIND_DOCUMENTS,
                WorkflowActionType.PRESENT_DOCUMENTS,
            ],
        )

    def test_plan_compiler_does_not_add_present_documents_when_output_step_exists(self) -> None:
        output_actions = (
            WorkflowActionType.PRESENT_DOCUMENTS,
            WorkflowActionType.ANSWER_QUESTION,
            WorkflowActionType.SUMMARIZE_DOCUMENTS,
            WorkflowActionType.GENERATE_DRAFT,
            WorkflowActionType.EXPLORE_IDEAS,
            WorkflowActionType.RECOMMEND_DOCUMENTS,
            WorkflowActionType.SYNTHESIZE_REPORT,
            WorkflowActionType.PLAN_HOST_ACTIONS,
        )

        for output_action in output_actions:
            with self.subTest(output_action=output_action):
                if output_action == WorkflowActionType.SYNTHESIZE_REPORT:
                    actions = [
                        WorkflowAction(action_type=WorkflowActionType.FIND_DOCUMENTS),
                        WorkflowAction(action_type=WorkflowActionType.CLASSIFY_DOCUMENTS),
                        WorkflowAction(
                            action_type=WorkflowActionType.ANALYZE_DOCUMENTS,
                            params={"instruction": "Summarize each relevant document."},
                        ),
                        WorkflowAction(action_type=output_action),
                    ]
                else:
                    params = (
                        {"instruction": "Generate an output."}
                        if output_action
                        in {
                            WorkflowActionType.ANSWER_QUESTION,
                            WorkflowActionType.SUMMARIZE_DOCUMENTS,
                            WorkflowActionType.GENERATE_DRAFT,
                            WorkflowActionType.EXPLORE_IDEAS,
                        }
                        else {}
                    )
                    actions = [
                        WorkflowAction(action_type=WorkflowActionType.FIND_DOCUMENTS),
                        WorkflowAction(action_type=output_action, params=params),
                    ]
                plan = WorkflowPlan(intent="answer", actions=actions)

                execution_plan = WorkflowPlanCompiler().compile(plan)

                self.assertEqual(
                    [step.action_type for step in execution_plan.steps],
                    [action.action_type for action in actions],
                )

    def test_workflow_plan_rejects_unknown_fields_and_boolean_coercion(self) -> None:
        invalid_payloads = (
            {
                "intent": "answer",
                "unexpected": "ignored-before",
                "actions": [{"type": "find_documents"}],
            },
            {
                "intent": "answer",
                "actions": [{"type": "find_documents", "unexpected": "ignored-before"}],
            },
            {
                "intent": "answer",
                "requires_confirmation": "false",
                "actions": [{"type": "find_documents"}],
            },
            {
                "intent": "answer",
                "actions": [
                    {
                        "type": "find_documents",
                        "requires_confirmation": "false",
                    }
                ],
            },
        )

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    workflow_plan_from_mapping(payload)

    def test_requested_host_actions_reject_unknown_or_malformed_values(self) -> None:
        self.assertEqual(requested_host_actions({}), ())
        self.assertEqual(
            requested_host_actions({"host_actions": ["create_document"]}),
            (HostActionType.CREATE_DOCUMENT,),
        )
        self.assertEqual(
            requested_host_actions({"host_actions": " create_document "}),
            (HostActionType.CREATE_DOCUMENT,),
        )

        with self.assertRaises(ValueError):
            requested_host_actions({"host_actions": ["write_file"]})
        with self.assertRaises(TypeError):
            requested_host_actions({"host_actions": [None]})
        with self.assertRaises(TypeError):
            requested_host_actions({"host_actions": None})

    def test_string_tuple_rejects_non_string_items(self) -> None:
        self.assertEqual(string_tuple(["folder-a", " folder-b "]), ("folder-a", "folder-b"))

        with self.assertRaises(TypeError):
            string_tuple(["folder-a", None])

    def test_document_from_task_does_not_stringify_null_values(self) -> None:
        state = WorkflowState(
            task=TaskSnapshot(
                task_id="task-1",
                tenant="tenant-1",
                request="Recommend a folder.",
                context=TaskContext(requested_at="2026-05-17T09:30:00+09:00"),
                status=TaskStatus.CLARIFICATION_REQUIRED,
                analysis=TaskAnalysis(message="Planning."),
            )
        )
        query = RetrievalQuery(
            text="Recommend a folder.",
            request_context=RequestContext(
                tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"
            ),
        )

        document = document_from_task(
            state,
            query,
            {
                "document_id": None,
                "title": None,
                "body": None,
            },
        )

        self.assertEqual(document.document_id, "")
        self.assertEqual(document.title, "")
        self.assertEqual(document.body, query.text)

        with self.assertRaises(TypeError):
            document_from_task(state, query, {"document_id": 123})

    def test_document_from_task_rejects_malformed_task_document_metadata(self) -> None:
        state = WorkflowState(
            task=TaskSnapshot(
                task_id="task-1",
                tenant="tenant-1",
                request="Recommend a folder.",
                context=TaskContext(requested_at="2026-05-17T09:30:00+09:00"),
                status=TaskStatus.CLARIFICATION_REQUIRED,
                analysis=TaskAnalysis(message="Planning."),
                metadata={"document": ["invalid"]},
            )
        )
        query = RetrievalQuery(
            text="Recommend a folder.",
            request_context=RequestContext(
                tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"
            ),
        )

        with self.assertRaises(TypeError):
            document_from_task(state, query, {})

    def test_document_from_task_normalizes_identity_options_only(self) -> None:
        state = WorkflowState(
            task=TaskSnapshot(
                task_id="task-1",
                tenant="tenant-1",
                request="Recommend a folder.",
                context=TaskContext(requested_at="2026-05-17T09:30:00+09:00"),
                status=TaskStatus.CLARIFICATION_REQUIRED,
                analysis=TaskAnalysis(message="Planning."),
                metadata={
                    "document": {
                        "document_type": " document ",
                        "document_id": " doc-1 ",
                        "source_version": " v1 ",
                    }
                },
            )
        )
        query = RetrievalQuery(
            text="Recommend a folder.",
            request_context=RequestContext(
                tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"
            ),
        )

        document = document_from_task(
            state,
            query,
            {
                "title": " Title ",
                "body": " Body ",
            },
        )

        self.assertEqual(document.document_type, "document")
        self.assertEqual(document.document_id, "doc-1")
        self.assertEqual(document.source_version, "v1")
        self.assertEqual(document.title, " Title ")
        self.assertEqual(document.body, " Body ")


if __name__ == "__main__":
    unittest.main()
