from __future__ import annotations

from foldmind_ai_core.core.application.workflows.state.execution import (
    OutputSpec,
    StepSpec,
    WorkflowArtifactName,
)
from foldmind_ai_core.core.application.workflows.state.plan import WorkflowActionType
from foldmind_ai_core.core.domain.models.tasks import TaskOutputType

STEP_SPECS: dict[WorkflowActionType, StepSpec] = {
    WorkflowActionType.FIND_DOCUMENTS: StepSpec(
        writes=(
            WorkflowArtifactName.DOCUMENT_RETRIEVAL,
            WorkflowArtifactName.CANDIDATE_DOCUMENTS,
        ),
    ),
    WorkflowActionType.PRESENT_DOCUMENTS: StepSpec(
        writes=(WorkflowArtifactName.DOCUMENT_SEARCH_RESULT,),
        reads=(WorkflowArtifactName.DOCUMENT_RETRIEVAL,),
        output=OutputSpec(
            output_type=TaskOutputType.DOCUMENT_SEARCH_RESULT,
            output_key="document_search_result",
            title="Document search result",
        ),
    ),
    WorkflowActionType.FIND_SIGNALS: StepSpec(
        writes=(WorkflowArtifactName.SIGNAL_RETRIEVAL,),
    ),
    WorkflowActionType.PRESENT_SIGNALS: StepSpec(
        writes=(WorkflowArtifactName.SIGNAL_SEARCH_RESULT,),
        reads=(WorkflowArtifactName.SIGNAL_RETRIEVAL,),
        output=OutputSpec(
            output_type=TaskOutputType.SUMMARY,
            output_key="signal_search_result",
            title="Signal search result",
        ),
    ),
    WorkflowActionType.EXPAND_SIGNAL_EVIDENCE: StepSpec(
        writes=(WorkflowArtifactName.SIGNAL_EVIDENCE,),
        reads=(WorkflowArtifactName.SIGNAL_RETRIEVAL,),
    ),
    WorkflowActionType.SYNTHESIZE_SIGNALS: StepSpec(
        writes=(WorkflowArtifactName.SUMMARY,),
        reads=(
            WorkflowArtifactName.SIGNAL_RETRIEVAL,
            WorkflowArtifactName.SIGNAL_EVIDENCE,
        ),
        output=OutputSpec(
            output_type=TaskOutputType.SUMMARY,
            output_key="summary",
            title="Summary",
        ),
    ),
    WorkflowActionType.EXTRACT_ON_DEMAND_SIGNALS: StepSpec(
        writes=(
            WorkflowArtifactName.SIGNAL_RETRIEVAL,
            WorkflowArtifactName.SIGNAL_EVIDENCE,
        ),
        reads=(WorkflowArtifactName.SIGNAL_RETRIEVAL,),
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
    WorkflowActionType.REQUEST_CLARIFICATION: StepSpec(
        writes=(WorkflowArtifactName.CLARIFICATION,),
        output=OutputSpec(
            output_type=TaskOutputType.CLARIFICATION,
            output_key="clarification",
            title="Clarification",
        ),
    ),
}
