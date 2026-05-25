from __future__ import annotations

from foldmind_ai_core.adapters.inbound.http.dtos.retrieval import FolderRecommendationDTO
from foldmind_ai_core.adapters.inbound.http.dtos.workflow_outputs import (
    AssistantClarificationDTO,
    DocumentRecommendationDTO,
    DocumentRecommendationResultDTO,
    DocumentSearchItemDTO,
    DocumentSearchResultDTO,
    DraftResultDTO,
    FolderRecommendationResultDTO,
    GeneratedTextDTO,
    RelatedRecommendationItemDTO,
    RelatedRecommendationResultDTO,
)
from foldmind_ai_core.adapters.inbound.http.mappers.documents import (
    retrieved_document_dto_from_result,
)
from foldmind_ai_core.adapters.inbound.http.mappers.retrieval import (
    retrieval_result_dto_from_result,
)
from foldmind_ai_core.core.application.models.generation import (
    AssistantClarification,
    DocumentRecommendation,
    DocumentRecommendationResult,
    DocumentSearchResult,
    DraftResult,
    FolderRecommendation,
    FolderRecommendationResult,
    GeneratedTextResult,
    RelatedRecommendationResult,
)


def generated_text_dto_from_result(
    result: GeneratedTextResult,
) -> GeneratedTextDTO:
    return GeneratedTextDTO(
        text=result.text,
        citations=[
            retrieval_result_dto_from_result(citation)
            for citation in result.citations
        ],
    )


def assistant_clarification_dto_from_result(
    clarification: AssistantClarification,
) -> AssistantClarificationDTO:
    return AssistantClarificationDTO(
        question=clarification.question,
        reason=clarification.reason,
    )


def draft_result_dto_from_result(result: DraftResult) -> DraftResultDTO:
    return DraftResultDTO(
        draft=result.draft,
        citations=[
            retrieval_result_dto_from_result(citation)
            for citation in result.citations
        ],
    )


def document_recommendation_dto_from_result(
    recommendation: DocumentRecommendation,
) -> DocumentRecommendationDTO:
    return DocumentRecommendationDTO(
        document=retrieved_document_dto_from_result(recommendation.document),
        reason=recommendation.reason,
        score=recommendation.score,
        evidence=[
            retrieval_result_dto_from_result(evidence)
            for evidence in recommendation.evidence
        ],
    )


def document_recommendation_result_dto_from_result(
    result: DocumentRecommendationResult,
) -> DocumentRecommendationResultDTO:
    return DocumentRecommendationResultDTO(
        primary=(
            document_recommendation_dto_from_result(result.primary)
            if result.primary is not None
            else None
        ),
        alternatives=[
            document_recommendation_dto_from_result(recommendation)
            for recommendation in result.alternatives
        ],
        confidence=result.confidence,
    )


def document_search_item_dto_from_result(
    item: DocumentRecommendation,
) -> DocumentSearchItemDTO:
    return DocumentSearchItemDTO(
        document=retrieved_document_dto_from_result(item.document),
        score=item.score,
        reason=item.reason,
        evidence=[
            retrieval_result_dto_from_result(evidence)
            for evidence in item.evidence
        ],
    )


def document_search_result_dto_from_result(
    result: DocumentSearchResult,
) -> DocumentSearchResultDTO:
    return DocumentSearchResultDTO(
        items=[
            document_search_item_dto_from_result(item)
            for item in result.items
        ],
        confidence=result.confidence,
    )


def folder_recommendation_dto_from_result(
    recommendation: FolderRecommendation,
) -> FolderRecommendationDTO:
    return FolderRecommendationDTO(
        folder_id=recommendation.folder_id,
        reason=recommendation.reason,
        score=recommendation.score,
    )


def folder_recommendation_result_dto_from_result(
    result: FolderRecommendationResult,
) -> FolderRecommendationResultDTO:
    return FolderRecommendationResultDTO(
        primary=folder_recommendation_dto_from_result(result.primary),
        alternatives=[
            folder_recommendation_dto_from_result(recommendation)
            for recommendation in result.alternatives
        ],
        confidence=result.confidence,
    )


def related_recommendation_item_dto_from_result(
    item: DocumentRecommendation | FolderRecommendation,
) -> RelatedRecommendationItemDTO:
    return RelatedRecommendationItemDTO(
        score=item.score,
        reason=item.reason,
        document=(
            document_recommendation_dto_from_result(item)
            if isinstance(item, DocumentRecommendation)
            else None
        ),
        folder=(
            folder_recommendation_dto_from_result(item)
            if isinstance(item, FolderRecommendation)
            else None
        ),
    )


def related_recommendation_result_dto_from_result(
    result: RelatedRecommendationResult,
) -> RelatedRecommendationResultDTO:
    return RelatedRecommendationResultDTO(
        items=[
            related_recommendation_item_dto_from_result(item)
            for item in result.items
        ],
        confidence=result.confidence,
    )
