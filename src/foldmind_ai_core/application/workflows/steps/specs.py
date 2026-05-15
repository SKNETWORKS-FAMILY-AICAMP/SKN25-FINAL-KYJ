from __future__ import annotations

from foldmind_ai_core.application.workflows.state.execution import (
    OutputSpec,
    StepSpec,
    WorkflowArtifactName,
)
from foldmind_ai_core.application.workflows.state.plan import WorkflowActionType
from foldmind_ai_core.domain.workflow.tasks import TaskOutputType

STEP_SPECS: dict[WorkflowActionType, StepSpec] = {
    WorkflowActionType.FIND_DOCUMENTS: StepSpec(
        writes=(
            WorkflowArtifactName.DOCUMENT_RETRIEVAL,
            WorkflowArtifactName.CANDIDATE_DOCUMENTS,
        ),
    ),
    WorkflowActionType.FIND_FOLDERS: StepSpec(
        writes=(WorkflowArtifactName.FOLDER_RETRIEVAL,),
    ),
    WorkflowActionType.FIND_RELATED: StepSpec(
        writes=(WorkflowArtifactName.RELATED_RETRIEVAL,),
    ),
    WorkflowActionType.CLASSIFY_DOCUMENTS: StepSpec(
        writes=(WorkflowArtifactName.RELEVANT_DOCUMENTS,),
        reads=(WorkflowArtifactName.CANDIDATE_DOCUMENTS,),
    ),
    WorkflowActionType.ANALYZE_DOCUMENTS: StepSpec(
        writes=(WorkflowArtifactName.DOCUMENT_SUMMARIES,),
        reads=(
            WorkflowArtifactName.RELEVANT_DOCUMENTS,
            WorkflowArtifactName.DOCUMENT_RETRIEVAL,
        ),
    ),
    WorkflowActionType.SYNTHESIZE_REPORT: StepSpec(
        writes=(WorkflowArtifactName.SYNTHESIZED_REPORT,),
        reads=(WorkflowArtifactName.DOCUMENT_SUMMARIES,),
        output=OutputSpec(
            output_type=TaskOutputType.SUMMARY,
            output_key="synthesized_report",
            title="Synthesized report",
        ),
    ),
    WorkflowActionType.RECOMMEND_DOCUMENTS: StepSpec(
        writes=(WorkflowArtifactName.DOCUMENT_RECOMMENDATION,),
        reads=(WorkflowArtifactName.DOCUMENT_RETRIEVAL,),
        output=OutputSpec(
            output_type=TaskOutputType.DOCUMENT_RECOMMENDATION,
            output_key="document_recommendation",
            title="Document recommendation",
        ),
    ),
    WorkflowActionType.RECOMMEND_FOLDER: StepSpec(
        writes=(WorkflowArtifactName.FOLDER_RECOMMENDATION,),
        output=OutputSpec(
            output_type=TaskOutputType.FOLDER_RECOMMENDATION,
            output_key="folder_recommendation",
            title="Folder recommendation",
        ),
    ),
    WorkflowActionType.RECOMMEND_RELATED: StepSpec(
        writes=(WorkflowArtifactName.RELATED_RECOMMENDATION,),
        reads=(
            WorkflowArtifactName.DOCUMENT_RECOMMENDATION,
            WorkflowArtifactName.FOLDER_RECOMMENDATION,
        ),
        output=OutputSpec(
            output_type=TaskOutputType.RELATED_RECOMMENDATION,
            output_key="related_recommendation",
            title="Related recommendation",
        ),
    ),
    WorkflowActionType.ANSWER_QUESTION: StepSpec(
        writes=(WorkflowArtifactName.ANSWER,),
        reads=(WorkflowArtifactName.DOCUMENT_RETRIEVAL,),
        output=OutputSpec(
            output_type=TaskOutputType.ANSWER,
            output_key="answer",
            title="Answer",
        ),
    ),
    WorkflowActionType.SUMMARIZE_DOCUMENTS: StepSpec(
        writes=(WorkflowArtifactName.SUMMARY,),
        reads=(WorkflowArtifactName.DOCUMENT_RETRIEVAL,),
        output=OutputSpec(
            output_type=TaskOutputType.SUMMARY,
            output_key="summary",
            title="Summary",
        ),
    ),
    WorkflowActionType.GENERATE_DRAFT: StepSpec(
        writes=(WorkflowArtifactName.DRAFT,),
        reads=(WorkflowArtifactName.DOCUMENT_RETRIEVAL,),
        output=OutputSpec(
            output_type=TaskOutputType.DRAFT,
            output_key="draft",
            title="Draft",
        ),
    ),
    WorkflowActionType.EXPLORE_IDEAS: StepSpec(
        writes=(WorkflowArtifactName.IDEAS,),
        reads=(WorkflowArtifactName.DOCUMENT_RETRIEVAL,),
        output=OutputSpec(
            output_type=TaskOutputType.IDEAS,
            output_key="ideas",
            title="Ideas",
        ),
    ),
    WorkflowActionType.PLAN_HOST_ACTIONS: StepSpec(
        writes=(WorkflowArtifactName.ACTION_PLAN,),
        output=OutputSpec(
            output_type=TaskOutputType.ACTION_PLAN,
            output_key="action_plan",
            title="Action plan",
        ),
    ),
}
