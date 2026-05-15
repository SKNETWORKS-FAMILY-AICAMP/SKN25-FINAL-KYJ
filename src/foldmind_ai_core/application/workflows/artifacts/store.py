from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from foldmind_ai_core.application.workflows.state.execution import (
    OutputSpec,
    StepOutcome,
    WorkflowArtifactName,
)
from foldmind_ai_core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.domain.generation.results import (
    DocumentRecommendationResult,
    DraftResult,
    FolderRecommendationResult,
    GeneratedTextResult,
    RelatedRecommendationResult,
)
from foldmind_ai_core.domain.retrieval.results import (
    FolderRetrievalResult,
    RetrievalResult,
    RetrievedDocument,
)
from foldmind_ai_core.domain.workflow.tasks import TaskOutput, TaskOutputResult, TaskOutputType
from foldmind_ai_core.shared.internal_ids import new_internal_id

T = TypeVar("T")


@dataclass(slots=True)
class WorkflowArtifactStore:
    def record_step_outcome(
        self,
        state: WorkflowState,
        outcome: StepOutcome,
        output: OutputSpec | None,
    ) -> None:
        for artifact_name, value in outcome.artifacts.items():
            self.__set(state, artifact_name, value)
        if output is not None and outcome.output is not None:
            self.__append_output(
                state,
                output_type=output.output_type,
                result=outcome.output,
                output_key=output.output_key,
                title=output.title,
            )

    def document_retrieval(self, state: WorkflowState) -> list[RetrievalResult]:
        return self.__get_list(
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

    def __set(
        self,
        state: WorkflowState,
        name: WorkflowArtifactName,
        value: object,
    ) -> None:
        state.artifacts.write(name, value)

    def __get(
        self,
        state: WorkflowState,
        name: WorkflowArtifactName,
        expected_type: type[T],
    ) -> T | None:
        value = self.__read(state, name)
        if value is None:
            return None
        return self.__typed_value(name, value, expected_type)

    def __get_list(
        self,
        state: WorkflowState,
        name: WorkflowArtifactName,
        item_type: type[T],
    ) -> list[T]:
        value = self.__read(state, name)
        if value is None:
            return []
        return self.__typed_list(name, value, item_type)

    def __get_optional_list(
        self,
        state: WorkflowState,
        name: WorkflowArtifactName,
        item_type: type[T],
    ) -> list[T] | None:
        value = self.__read(state, name)
        if value is None:
            return None
        return self.__typed_list(name, value, item_type)

    def __append_output(
        self,
        state: WorkflowState,
        *,
        output_type: TaskOutputType,
        result: TaskOutputResult,
        output_key: str,
        title: str,
    ) -> None:
        state.task.analysis.outputs.append(
            TaskOutput(
                output_type=output_type,
                result=result,
                output_id=new_internal_id(),
                title=title,
                metadata={"output_key": output_key},
            )
        )

    def __read(self, state: WorkflowState, name: WorkflowArtifactName) -> object | None:
        return state.artifacts.read(name)

    def __typed_value(
        self,
        name: WorkflowArtifactName,
        value: object,
        expected_type: type[T],
    ) -> T:
        if not isinstance(value, expected_type):
            raise TypeError(f"{name} artifact must contain {expected_type.__name__}.")
        return value

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
