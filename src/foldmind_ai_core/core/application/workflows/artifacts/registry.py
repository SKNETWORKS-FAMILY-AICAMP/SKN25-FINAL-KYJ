from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from foldmind_ai_core.core.application.workflows.state.execution import (
    OutputSpec,
    StepOutcome,
    WorkflowArtifactName,
)
from foldmind_ai_core.core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.core.application.models.generation import (
    DocumentRecommendationResult,
    DraftResult,
    FolderRecommendationResult,
    GeneratedTextResult,
    RelatedRecommendationResult,
)
from foldmind_ai_core.core.application.models.retrieval import (
    FolderRetrievalResult,
    RetrievalResult,
    RetrievedDocument,
    SignalRetrievalResult,
)
from foldmind_ai_core.core.domain.models.tasks import (
    TaskFinalResult,
    TaskJob,
    TaskJobResult,
)
from foldmind_ai_core.shared.types import JsonObject

T = TypeVar("T")


@dataclass(slots=True)
class WorkflowArtifactRegistry:
    def record_step_outcome(
        self,
        state: WorkflowState,
        job: TaskJob,
        outcome: StepOutcome,
        output: OutputSpec | None,
    ) -> None:
        for artifact_name, value in outcome.artifacts.items():
            state.artifacts.items[artifact_name] = value
        if output is not None and outcome.output is not None:
            job_result = TaskJobResult(
                result_type=output.output_type.value,
                result=outcome.output,
                summary={
                    "output_key": output.output_key,
                    "title": output.title,
                },
                metadata={"output_key": output.output_key},
            )
            job.results.append(job_result)
            state.task.result = TaskFinalResult(
                result_type=output.output_type,
                result=outcome.output,
                title=output.title,
                metadata={"output_key": output.output_key, "job_id": job.job_id},
            )
            return
        if outcome.artifacts:
            artifact_names = [artifact.value for artifact in outcome.artifacts]
            manifest: JsonObject = {
                "artifacts_written": list(artifact_names),
                "artifact_count": len(artifact_names),
            }
            job.results.append(
                TaskJobResult(
                    result_type="artifact_manifest",
                    result=manifest,
                    summary=manifest,
                )
            )

    def document_retrieval(self, state: WorkflowState) -> list[RetrievalResult]:
        return self.__get_list(
            state,
            WorkflowArtifactName.DOCUMENT_RETRIEVAL,
            RetrievalResult,
        )

    def optional_document_retrieval(
        self,
        state: WorkflowState,
    ) -> list[RetrievalResult] | None:
        return self.__get_optional_list(
            state,
            WorkflowArtifactName.DOCUMENT_RETRIEVAL,
            RetrievalResult,
        )

    def folder_retrieval(self, state: WorkflowState) -> list[FolderRetrievalResult] | None:
        return self.__get_optional_list(
            state,
            WorkflowArtifactName.FOLDER_RETRIEVAL,
            FolderRetrievalResult,
        )

    def signal_retrieval(self, state: WorkflowState) -> list[SignalRetrievalResult]:
        return self.__get_list(
            state,
            WorkflowArtifactName.SIGNAL_RETRIEVAL,
            SignalRetrievalResult,
        )

    def optional_signal_evidence(
        self,
        state: WorkflowState,
    ) -> list[RetrievalResult] | None:
        return self.__get_optional_list(
            state,
            WorkflowArtifactName.SIGNAL_EVIDENCE,
            RetrievalResult,
        )

    def candidate_documents(self, state: WorkflowState) -> list[RetrievedDocument] | None:
        return self.__get_optional_list(
            state,
            WorkflowArtifactName.CANDIDATE_DOCUMENTS,
            RetrievedDocument,
        )

    def relevant_documents(self, state: WorkflowState) -> list[RetrievedDocument] | None:
        return self.__get_optional_list(
            state,
            WorkflowArtifactName.RELEVANT_DOCUMENTS,
            RetrievedDocument,
        )

    def document_recommendation(
        self,
        state: WorkflowState,
    ) -> DocumentRecommendationResult | None:
        return self.__get(
            state,
            WorkflowArtifactName.DOCUMENT_RECOMMENDATION,
            DocumentRecommendationResult,
        )

    def draft(self, state: WorkflowState) -> DraftResult | None:
        return self.__get(state, WorkflowArtifactName.DRAFT, DraftResult)

    def summary(self, state: WorkflowState) -> GeneratedTextResult | None:
        return self.__get(state, WorkflowArtifactName.SUMMARY, GeneratedTextResult)

    def synthesized_report(self, state: WorkflowState) -> GeneratedTextResult | None:
        return self.__get(state, WorkflowArtifactName.SYNTHESIZED_REPORT, GeneratedTextResult)

    def folder_recommendation(self, state: WorkflowState) -> FolderRecommendationResult | None:
        return self.__get(
            state,
            WorkflowArtifactName.FOLDER_RECOMMENDATION,
            FolderRecommendationResult,
        )

    def related_recommendation(self, state: WorkflowState) -> RelatedRecommendationResult | None:
        return self.__get(
            state,
            WorkflowArtifactName.RELATED_RECOMMENDATION,
            RelatedRecommendationResult,
        )

    def document_summaries(self, state: WorkflowState) -> list[GeneratedTextResult]:
        return self.__get_list(
            state,
            WorkflowArtifactName.DOCUMENT_SUMMARIES,
            GeneratedTextResult,
        )

    def optional_document_summaries(
        self,
        state: WorkflowState,
    ) -> list[GeneratedTextResult] | None:
        return self.__get_optional_list(
            state,
            WorkflowArtifactName.DOCUMENT_SUMMARIES,
            GeneratedTextResult,
        )

    def __get(
        self,
        state: WorkflowState,
        name: WorkflowArtifactName,
        expected_type: type[T],
    ) -> T | None:
        value = state.artifacts.items.get(name)
        if value is None:
            return None
        if not isinstance(value, expected_type):
            raise TypeError(f"{name} artifact must contain {expected_type.__name__}.")
        return value

    def __get_list(
        self,
        state: WorkflowState,
        name: WorkflowArtifactName,
        item_type: type[T],
    ) -> list[T]:
        value = state.artifacts.items.get(name)
        if value is None:
            return []
        return self.__typed_list(name, value, item_type)

    def __get_optional_list(
        self,
        state: WorkflowState,
        name: WorkflowArtifactName,
        item_type: type[T],
    ) -> list[T] | None:
        value = state.artifacts.items.get(name)
        if value is None:
            return None
        return self.__typed_list(name, value, item_type)

    def __typed_list(
        self,
        name: WorkflowArtifactName,
        value: object,
        item_type: type[T],
    ) -> list[T]:
        if not isinstance(value, list):
            raise TypeError(f"{name} artifact must be a list.")
        if not all(isinstance(item, item_type) for item in value):
            raise TypeError(f"{name} artifact must contain {item_type.__name__} items.")
        return value
