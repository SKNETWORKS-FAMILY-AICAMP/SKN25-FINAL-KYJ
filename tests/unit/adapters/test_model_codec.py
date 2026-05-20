from __future__ import annotations

import unittest

from foldmind_ai_core.adapters.outbound.domain_model_codec import (
    domain_model_json,
    restore_domain_model_json,
)
from foldmind_ai_core.adapters.outbound.workflow_runtime.checkpoint_codec import (
    workflow_state_from_checkpoint,
    workflow_state_to_checkpoint,
)
from foldmind_ai_core.core.application.workflows.state.execution import (
    WorkflowArtifactName,
    WorkflowExecutionPlan,
    WorkflowStep,
    WorkflowStepInput,
)
from foldmind_ai_core.core.application.workflows.state.plan import WorkflowActionType
from foldmind_ai_core.core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.core.domain.models.workflow.actions import (
    HostAction,
    HostActionType,
    UpdateDocumentInput,
)
from foldmind_ai_core.core.domain.models.generation.results import (
    DocumentSearchItem,
    DocumentSearchResult,
)
from foldmind_ai_core.core.domain.models.retrieval.results import RetrievedDocument
from foldmind_ai_core.core.domain.models.workflow.tasks import TaskAnalysis, TaskContext, TaskSnapshot, TaskStatus


class DomainModelCodecTests(unittest.TestCase):
    def test_domain_model_codec_restores_document_search_result(self) -> None:
        result = DocumentSearchResult(
            items=[
                DocumentSearchItem(
                    document=RetrievedDocument(
                        tenant="tenant-1",
                        document_type="document",
                        document_id="doc-1",
                        source_version="v1",
                    ),
                    score=0.9,
                    reason="Document matches the search request.",
                )
            ]
        )

        restored = restore_domain_model_json(domain_model_json(result), DocumentSearchResult)

        self.assertEqual(restored, result)

    def test_domain_model_codec_restores_update_document_metadata(self) -> None:
        encoded = domain_model_json(
            UpdateDocumentInput(
                document_type="document",
                document_id="doc-1",
                metadata={"source_tags": ["startup", "research"]},
            )
        )

        restored = restore_domain_model_json(encoded, UpdateDocumentInput)

        self.assertEqual(restored.metadata, {"source_tags": ["startup", "research"]})

    def test_checkpoint_codec_restores_metadata_inside_actions(self) -> None:
        action = HostAction(
            action_type=HostActionType.UPDATE_DOCUMENT,
            summary="Update document metadata.",
            input=UpdateDocumentInput(
                document_type="document",
                document_id="doc-1",
                metadata={"source_tags": ["startup"]},
            ),
        )
        checkpoint = workflow_state_to_checkpoint(
            WorkflowState(
                task=TaskSnapshot(
                    task_id="task-1",
                    tenant="tenant-1",
                    request="Update the document metadata.",
                    context=TaskContext(requested_at="2026-05-17T09:30:00+09:00"),
                    status=TaskStatus.AWAITING_DECISION,
                    analysis=TaskAnalysis(message="Awaiting decision."),
                    host_actions=[action],
                )
            )
        )

        restored = workflow_state_from_checkpoint(checkpoint)
        restored_input = restored.task.host_actions[0].input

        self.assertIsInstance(restored_input, UpdateDocumentInput)
        self.assertEqual(restored_input.metadata, {"source_tags": ["startup"]})

    def test_checkpoint_codec_restores_enum_tuple_fields(self) -> None:
        checkpoint = workflow_state_to_checkpoint(
            WorkflowState(
                task=TaskSnapshot(
                    task_id="task-1",
                    tenant="tenant-1",
                    request="Summarize documents.",
                    context=TaskContext(requested_at="2026-05-17T09:30:00+09:00"),
                    status=TaskStatus.CLARIFICATION_REQUIRED,
                    analysis=TaskAnalysis(message="Planning."),
                ),
                plan=WorkflowExecutionPlan(
                    steps=[
                        WorkflowStep(
                            action_type=WorkflowActionType.SYNTHESIZE_REPORT,
                            step_input=WorkflowStepInput(
                                artifact_refs=(
                                    WorkflowArtifactName.DOCUMENT_SUMMARIES,
                                )
                            ),
                        )
                    ]
                ),
            )
        )

        restored = workflow_state_from_checkpoint(checkpoint)
        artifact_refs = restored.plan.steps[0].step_input.artifact_refs

        self.assertEqual(
            artifact_refs,
            (WorkflowArtifactName.DOCUMENT_SUMMARIES,),
        )
        self.assertIsInstance(artifact_refs[0], WorkflowArtifactName)

    def test_checkpoint_codec_rejects_malformed_runtime_counters(self) -> None:
        checkpoint = workflow_state_to_checkpoint(
            WorkflowState(
                task=TaskSnapshot(
                    task_id="task-1",
                    tenant="tenant-1",
                    request="Run task.",
                    context=TaskContext(requested_at="2026-05-17T09:30:00+09:00"),
                    status=TaskStatus.CLARIFICATION_REQUIRED,
                    analysis=TaskAnalysis(message="Planning."),
                ),
            )
        )

        malformed_version = dict(checkpoint)
        malformed_version["state_version"] = True
        with self.assertRaises(ValueError):
            workflow_state_from_checkpoint(malformed_version)

        negative_step = dict(checkpoint)
        negative_step["next_step_index"] = -1
        with self.assertRaises(ValueError):
            workflow_state_from_checkpoint(negative_step)

        negative_retry_count = dict(checkpoint)
        negative_retry_count["retry_counts"] = {"0:0:find_documents": -1}
        with self.assertRaises(ValueError):
            workflow_state_from_checkpoint(negative_retry_count)


if __name__ == "__main__":
    unittest.main()
