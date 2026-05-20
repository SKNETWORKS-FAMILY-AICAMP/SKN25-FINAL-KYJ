from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeAlias

from foldmind_ai_core.core.application.results.retrieval import RetrievedChunkResult
from foldmind_ai_core.shared.types import Metadata, JsonObject


@dataclass(frozen=True, slots=True)
class TaskContextResult:
    requested_at: str
    document_id: str | None = None
    folder_id: str | None = None


@dataclass(frozen=True, slots=True)
class TaskInputEntryResult:
    task_input_id: str
    input_text: str
    context: TaskContextResult
    position: int
    status: str


@dataclass(frozen=True, slots=True)
class TaskEventResult:
    event_id: str
    event_type: str
    message: str
    job_id: str | None = None
    data: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class HostActionPolicyResult:
    max_attempts: int = 1
    allow_skip: bool = False
    retryable: bool = False
    requires_confirmation: bool = True


@dataclass(frozen=True, slots=True)
class CreateFolderInputResult:
    name: str
    parent_folder_id: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CreateDocumentInputResult:
    title: str
    body: str
    folder_id: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class UpdateDocumentInputResult:
    document_type: str
    document_id: str
    title: str | None = None
    body: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MoveDocumentInputResult:
    document_type: str
    document_id: str
    target_folder_id: str
    source_folder_id: str | None = None


@dataclass(frozen=True, slots=True)
class LinkDocumentsInputResult:
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    relationship: str = "related"
    metadata: Metadata = field(default_factory=dict)


HostActionInputResult: TypeAlias = (
    CreateFolderInputResult
    | CreateDocumentInputResult
    | UpdateDocumentInputResult
    | MoveDocumentInputResult
    | LinkDocumentsInputResult
)


@dataclass(frozen=True, slots=True)
class HostActionItemResult:
    action_type: str
    summary: str
    input: HostActionInputResult
    action_id: str | None = None
    job_id: str | None = None
    reason: str = ""
    status: str = "proposed"
    attempts: int = 0
    policy: HostActionPolicyResult = field(default_factory=HostActionPolicyResult)
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ActionPlanResult:
    summary: str
    steps: tuple[str, ...]
    host_actions: tuple[HostActionItemResult, ...] = ()


@dataclass(frozen=True, slots=True)
class AssistantClarificationResult:
    question: str
    reason: str


@dataclass(frozen=True, slots=True)
class GeneratedTextTaskOutputResult:
    text: str
    citations: tuple[RetrievedChunkResult, ...] = ()


@dataclass(frozen=True, slots=True)
class DraftTaskOutputResult:
    draft: str
    citations: tuple[RetrievedChunkResult, ...] = ()


@dataclass(frozen=True, slots=True)
class RetrievedDocumentResult:
    tenant: str
    document_type: str
    document_id: str
    source_version: str
    created_at: str = ""
    updated_at: str = ""
    snippet: str = ""
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DocumentRecommendationItemResult:
    document: RetrievedDocumentResult
    reason: str
    score: float
    evidence: tuple[RetrievedChunkResult, ...] = ()


@dataclass(frozen=True, slots=True)
class DocumentRecommendationTaskOutputResult:
    primary: DocumentRecommendationItemResult | None = None
    alternatives: tuple[DocumentRecommendationItemResult, ...] = ()
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class DocumentSearchItemResult:
    document: RetrievedDocumentResult
    score: float
    reason: str
    evidence: tuple[RetrievedChunkResult, ...] = ()


@dataclass(frozen=True, slots=True)
class DocumentSearchTaskOutputResult:
    items: tuple[DocumentSearchItemResult, ...] = ()
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class FolderRecommendationItemResult:
    folder_id: str
    reason: str
    score: float


@dataclass(frozen=True, slots=True)
class FolderRecommendationTaskOutputResult:
    primary: FolderRecommendationItemResult
    alternatives: tuple[FolderRecommendationItemResult, ...] = ()
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class RelatedRecommendationItemResult:
    score: float
    reason: str
    document: DocumentRecommendationItemResult | None = None
    folder: FolderRecommendationItemResult | None = None


@dataclass(frozen=True, slots=True)
class RelatedRecommendationTaskOutputResult:
    items: tuple[RelatedRecommendationItemResult, ...] = ()
    confidence: float = 0.0


TaskOutputValueResult: TypeAlias = (
    AssistantClarificationResult
    | GeneratedTextTaskOutputResult
    | DraftTaskOutputResult
    | DocumentRecommendationTaskOutputResult
    | DocumentSearchTaskOutputResult
    | FolderRecommendationTaskOutputResult
    | RelatedRecommendationTaskOutputResult
    | ActionPlanResult
)


@dataclass(frozen=True, slots=True)
class TaskOutputItemResult:
    output_type: str
    result: TaskOutputValueResult
    output_id: str | None = None
    title: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TaskJobResultItemResult:
    job_result_id: str
    result_type: str
    summary: JsonObject = field(default_factory=dict)
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TaskJobItemResult:
    job_id: str
    round_index: int
    position: int
    job_type: str
    status: str
    reason: str = ""
    input: JsonObject = field(default_factory=dict)
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    metadata: Metadata = field(default_factory=dict)
    results: tuple[TaskJobResultItemResult, ...] = ()


@dataclass(frozen=True, slots=True)
class TaskFinalResultResult:
    result_type: str
    result: TaskOutputValueResult
    title: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TaskAnalysisResult:
    message: str


@dataclass(frozen=True, slots=True)
class TaskSnapshotResult:
    task_id: str
    tenant: str
    request: str
    context: TaskContextResult
    status: str
    analysis: TaskAnalysisResult
    inputs: tuple[TaskInputEntryResult, ...] = ()
    jobs: tuple[TaskJobItemResult, ...] = ()
    result: TaskFinalResultResult | None = None
    host_actions: tuple[HostActionItemResult, ...] = ()
    error: str | None = None
    current_action_id: str | None = None
    events: tuple[TaskEventResult, ...] = ()
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TaskResult:
    task: TaskSnapshotResult


@dataclass(frozen=True, slots=True)
class RecordActionResult:
    recorded: bool
    task: TaskSnapshotResult
