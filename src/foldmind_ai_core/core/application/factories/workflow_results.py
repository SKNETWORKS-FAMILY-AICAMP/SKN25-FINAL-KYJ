from __future__ import annotations

from foldmind_ai_core.core.application.factories.retrieval_results import (
    retrieved_chunk_result_from_domain,
)
from foldmind_ai_core.core.application.results.workflow import (
    ActionPlanResult,
    AssistantClarificationResult,
    CreateDocumentInputResult,
    CreateFolderInputResult,
    DocumentRecommendationItemResult,
    DocumentRecommendationTaskOutputResult,
    DocumentSearchItemResult,
    DocumentSearchTaskOutputResult,
    DraftTaskOutputResult,
    FolderRecommendationItemResult,
    FolderRecommendationTaskOutputResult,
    GeneratedTextTaskOutputResult,
    HostActionInputResult,
    HostActionItemResult,
    HostActionPolicyResult,
    LinkDocumentsInputResult,
    MoveDocumentInputResult,
    RecordActionResult,
    RelatedRecommendationItemResult,
    RelatedRecommendationTaskOutputResult,
    RetrievedDocumentResult,
    TaskAnalysisResult,
    TaskContextResult,
    TaskEventResult,
    TaskFinalResultResult,
    TaskJobItemResult,
    TaskJobResultItemResult,
    TaskOutputValueResult,
    TaskInputEntryResult,
    TaskResult,
    TaskSnapshotResult,
    UpdateDocumentInputResult,
)
from foldmind_ai_core.core.domain.models.generation.results import (
    AssistantClarification,
    DocumentRecommendation,
    DocumentRecommendationResult,
    DocumentSearchItem,
    DocumentSearchResult,
    DraftResult,
    FolderRecommendation,
    FolderRecommendationResult,
    GeneratedTextResult,
    RelatedRecommendationItem,
    RelatedRecommendationResult,
)
from foldmind_ai_core.core.domain.models.retrieval.results import RetrievedDocument
from foldmind_ai_core.core.domain.models.workflow.actions import (
    ActionPlan,
    CreateDocumentInput,
    CreateFolderInput,
    HostAction,
    HostActionInput,
    HostActionPolicy,
    LinkDocumentsInput,
    MoveDocumentInput,
    UpdateDocumentInput,
)
from foldmind_ai_core.core.domain.models.workflow.tasks import (
    TaskAnalysis,
    TaskContext,
    TaskEvent,
    TaskFinalResult,
    TaskJob,
    TaskJobResult,
    TaskInputEntry,
    TaskSnapshot,
)


def task_result_from_snapshot(snapshot: TaskSnapshot) -> TaskResult:
    return TaskResult(task=task_snapshot_result_from_domain(snapshot))


def record_action_result_from_snapshot(
    *,
    recorded: bool,
    snapshot: TaskSnapshot,
) -> RecordActionResult:
    return RecordActionResult(
        recorded=recorded,
        task=task_snapshot_result_from_domain(snapshot),
    )


def task_snapshot_result_from_domain(snapshot: TaskSnapshot) -> TaskSnapshotResult:
    return TaskSnapshotResult(
        task_id=snapshot.task_id,
        tenant=snapshot.tenant,
        request=snapshot.request,
        context=task_context_result_from_domain(snapshot.context),
        status=snapshot.status.value,
        analysis=task_analysis_result_from_domain(snapshot.analysis),
        inputs=tuple(
            task_input_entry_result_from_domain(task_input)
            for task_input in snapshot.inputs
        ),
        jobs=tuple(task_job_item_result_from_domain(job) for job in snapshot.jobs),
        result=(
            task_final_result_from_domain(snapshot.result)
            if snapshot.result is not None
            else None
        ),
        host_actions=tuple(
            host_action_item_result_from_domain(action)
            for action in snapshot.host_actions
        ),
        error=snapshot.error,
        current_action_id=snapshot.current_action_id,
        events=tuple(task_event_result_from_domain(event) for event in snapshot.events),
        metadata=dict(snapshot.metadata),
    )


def task_context_result_from_domain(context: TaskContext) -> TaskContextResult:
    return TaskContextResult(
        requested_at=context.requested_at,
        document_id=context.document_id,
        folder_id=context.folder_id,
    )


def task_input_entry_result_from_domain(
    task_input: TaskInputEntry,
) -> TaskInputEntryResult:
    return TaskInputEntryResult(
        task_input_id=task_input.task_input_id,
        input_text=task_input.input_text,
        context=task_context_result_from_domain(task_input.context),
        position=task_input.position,
        status=task_input.status.value,
    )


def task_event_result_from_domain(event: TaskEvent) -> TaskEventResult:
    return TaskEventResult(
        event_id=event.event_id,
        event_type=event.event_type.value,
        message=event.message,
        job_id=event.job_id,
        data=dict(event.data),
    )


def task_analysis_result_from_domain(analysis: TaskAnalysis) -> TaskAnalysisResult:
    return TaskAnalysisResult(message=analysis.message)


def task_job_item_result_from_domain(job: TaskJob) -> TaskJobItemResult:
    return TaskJobItemResult(
        job_id=job.job_id,
        round_index=job.round_index,
        position=job.position,
        job_type=job.job_type,
        status=job.status.value,
        reason=job.reason,
        input=dict(job.input),
        started_at=job.started_at,
        finished_at=job.finished_at,
        error=job.error,
        metadata=dict(job.metadata),
        results=tuple(
            task_job_result_item_result_from_domain(result)
            for result in job.results
        ),
    )


def task_job_result_item_result_from_domain(
    result: TaskJobResult,
) -> TaskJobResultItemResult:
    return TaskJobResultItemResult(
        job_result_id=result.job_result_id,
        result_type=result.result_type,
        summary=dict(result.summary),
        metadata=dict(result.metadata),
    )


def task_final_result_from_domain(result: TaskFinalResult) -> TaskFinalResultResult:
    return TaskFinalResultResult(
        result_type=result.result_type.value,
        result=task_output_value_result_from_domain(result.result),
        title=result.title,
        metadata=dict(result.metadata),
    )


def task_output_value_result_from_domain(value: object) -> TaskOutputValueResult:
    if isinstance(value, AssistantClarification):
        return AssistantClarificationResult(question=value.question, reason=value.reason)
    if isinstance(value, GeneratedTextResult):
        return GeneratedTextTaskOutputResult(
            text=value.text,
            citations=tuple(
                retrieved_chunk_result_from_domain(citation)
                for citation in value.citations
            ),
        )
    if isinstance(value, DraftResult):
        return DraftTaskOutputResult(
            draft=value.draft,
            citations=tuple(
                retrieved_chunk_result_from_domain(citation)
                for citation in value.citations
            ),
        )
    if isinstance(value, DocumentRecommendationResult):
        return document_recommendation_result_from_domain(value)
    if isinstance(value, DocumentSearchResult):
        return document_search_result_from_domain(value)
    if isinstance(value, FolderRecommendationResult):
        return folder_recommendation_result_from_domain(value)
    if isinstance(value, RelatedRecommendationResult):
        return related_recommendation_result_from_domain(value)
    if isinstance(value, ActionPlan):
        return action_plan_result_from_domain(value)
    raise TypeError(f"Unsupported task output result: {type(value).__name__}")


def retrieved_document_result_from_domain(
    document: RetrievedDocument,
) -> RetrievedDocumentResult:
    return RetrievedDocumentResult(
        tenant=document.tenant,
        document_type=document.document_type,
        document_id=document.document_id,
        source_version=document.source_version,
        created_at=document.created_at,
        updated_at=document.updated_at,
        snippet=document.snippet,
        metadata=dict(document.metadata),
    )


def document_recommendation_item_result_from_domain(
    recommendation: DocumentRecommendation,
) -> DocumentRecommendationItemResult:
    return DocumentRecommendationItemResult(
        document=retrieved_document_result_from_domain(recommendation.document),
        reason=recommendation.reason,
        score=recommendation.score,
        evidence=tuple(
            retrieved_chunk_result_from_domain(evidence)
            for evidence in recommendation.evidence
        ),
    )


def document_recommendation_result_from_domain(
    result: DocumentRecommendationResult,
) -> DocumentRecommendationTaskOutputResult:
    return DocumentRecommendationTaskOutputResult(
        primary=(
            document_recommendation_item_result_from_domain(result.primary)
            if result.primary is not None
            else None
        ),
        alternatives=tuple(
            document_recommendation_item_result_from_domain(recommendation)
            for recommendation in result.alternatives
        ),
        confidence=result.confidence,
    )


def document_search_item_result_from_domain(
    item: DocumentSearchItem,
) -> DocumentSearchItemResult:
    return DocumentSearchItemResult(
        document=retrieved_document_result_from_domain(item.document),
        score=item.score,
        reason=item.reason,
        evidence=tuple(
            retrieved_chunk_result_from_domain(evidence)
            for evidence in item.evidence
        ),
    )


def document_search_result_from_domain(
    result: DocumentSearchResult,
) -> DocumentSearchTaskOutputResult:
    return DocumentSearchTaskOutputResult(
        items=tuple(
            document_search_item_result_from_domain(item)
            for item in result.items
        ),
        confidence=result.confidence,
    )


def folder_recommendation_item_result_from_domain(
    recommendation: FolderRecommendation,
) -> FolderRecommendationItemResult:
    return FolderRecommendationItemResult(
        folder_id=recommendation.folder_id,
        reason=recommendation.reason,
        score=recommendation.score,
    )


def folder_recommendation_result_from_domain(
    result: FolderRecommendationResult,
) -> FolderRecommendationTaskOutputResult:
    return FolderRecommendationTaskOutputResult(
        primary=folder_recommendation_item_result_from_domain(result.primary),
        alternatives=tuple(
            folder_recommendation_item_result_from_domain(recommendation)
            for recommendation in result.alternatives
        ),
        confidence=result.confidence,
    )


def related_recommendation_item_result_from_domain(
    item: RelatedRecommendationItem,
) -> RelatedRecommendationItemResult:
    target = item.target
    return RelatedRecommendationItemResult(
        score=target.score,
        reason=target.reason,
        document=(
            document_recommendation_item_result_from_domain(target)
            if isinstance(target, DocumentRecommendation)
            else None
        ),
        folder=(
            folder_recommendation_item_result_from_domain(target)
            if isinstance(target, FolderRecommendation)
            else None
        ),
    )


def related_recommendation_result_from_domain(
    result: RelatedRecommendationResult,
) -> RelatedRecommendationTaskOutputResult:
    return RelatedRecommendationTaskOutputResult(
        items=tuple(
            related_recommendation_item_result_from_domain(item)
            for item in result.items
        ),
        confidence=result.confidence,
    )


def action_plan_result_from_domain(plan: ActionPlan) -> ActionPlanResult:
    return ActionPlanResult(
        summary=plan.summary,
        steps=tuple(plan.steps),
        host_actions=tuple(
            host_action_item_result_from_domain(action)
            for action in plan.host_actions
        ),
    )


def host_action_item_result_from_domain(action: HostAction) -> HostActionItemResult:
    return HostActionItemResult(
        action_type=action.action_type.value,
        summary=action.summary,
        input=host_action_input_result_from_domain(action.input),
        action_id=action.action_id,
        job_id=action.job_id,
        reason=action.reason,
        status=action.status.value,
        attempts=action.attempts,
        policy=host_action_policy_result_from_domain(action.policy),
        metadata=dict(action.metadata),
    )


def host_action_policy_result_from_domain(
    policy: HostActionPolicy,
) -> HostActionPolicyResult:
    return HostActionPolicyResult(
        max_attempts=policy.max_attempts,
        allow_skip=policy.allow_skip,
        retryable=policy.retryable,
        requires_confirmation=policy.requires_confirmation,
    )


def host_action_input_result_from_domain(
    action_input: HostActionInput,
) -> HostActionInputResult:
    if isinstance(action_input, CreateFolderInput):
        return CreateFolderInputResult(
            name=action_input.name,
            parent_folder_id=action_input.parent_folder_id,
            metadata=dict(action_input.metadata),
        )
    if isinstance(action_input, CreateDocumentInput):
        return CreateDocumentInputResult(
            title=action_input.title,
            body=action_input.body,
            folder_id=action_input.folder_id,
            metadata=dict(action_input.metadata),
        )
    if isinstance(action_input, UpdateDocumentInput):
        return UpdateDocumentInputResult(
            document_type=action_input.document_type,
            document_id=action_input.document_id,
            title=action_input.title,
            body=action_input.body,
            metadata=dict(action_input.metadata),
        )
    if isinstance(action_input, MoveDocumentInput):
        return MoveDocumentInputResult(
            document_type=action_input.document_type,
            document_id=action_input.document_id,
            target_folder_id=action_input.target_folder_id,
            source_folder_id=action_input.source_folder_id,
        )
    if isinstance(action_input, LinkDocumentsInput):
        return LinkDocumentsInputResult(
            source_type=action_input.source_type,
            source_id=action_input.source_id,
            target_type=action_input.target_type,
            target_id=action_input.target_id,
            relationship=action_input.relationship,
            metadata=dict(action_input.metadata),
        )
    raise TypeError(f"Unsupported host action input: {type(action_input).__name__}")
