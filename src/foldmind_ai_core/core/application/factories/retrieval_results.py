from __future__ import annotations

from typing import Iterable

from foldmind_ai_core.core.application.results.retrieval import (
    FolderSearchResultItem,
    FolderRecommendationResultItem,
    RecommendFolderResult,
    RetrievedChunkResult,
    RetrievedFolderResult,
    RetrievedSignalEvidenceResult,
    RetrievedSignalResult,
    SearchDocumentsResult,
    SearchFoldersResult,
    SearchSignalsResult,
    SignalSearchResultItem,
)
from foldmind_ai_core.core.domain.models.generation.results import (
    FolderRecommendation,
    FolderRecommendationResult,
)
from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.retrieval.results import (
    RetrievalResult,
    FolderRetrievalResult,
    RetrievedSignal,
    RetrievedSignalEvidence,
    RetrievedFolder,
    SignalRetrievalResult,
)


def retrieved_chunk_result_from_domain(result: RetrievalResult) -> RetrievedChunkResult:
    chunk = result.chunk
    return RetrievedChunkResult(
        tenant=chunk.tenant,
        document_type=chunk.document_type,
        document_id=chunk.document_id,
        source_version=chunk.source_version,
        document_index_input_digest=chunk.document_index_input_digest,
        created_at=chunk.created_at,
        updated_at=chunk.updated_at,
        chunk_id=chunk.chunk_id,
        chunk_index=chunk.chunk_index,
        chunking_version=chunk.chunking_version,
        text=chunk.text,
        text_hash=chunk.text_hash,
        start_offset=chunk.start_offset,
        end_offset=chunk.end_offset,
        embedding_model=chunk.embedding_model,
        embedding_version=chunk.embedding_version,
        index_schema_version=chunk.index_schema_version,
        score=result.score,
        metadata=dict(chunk.metadata),
    )


def retrieved_chunk_result_to_domain(result: RetrievedChunkResult) -> RetrievalResult:
    return RetrievalResult(
        chunk=DocumentChunk(
            tenant=result.tenant,
            document_type=result.document_type,
            document_id=result.document_id,
            source_version=result.source_version,
            document_index_input_digest=result.document_index_input_digest,
            created_at=result.created_at,
            updated_at=result.updated_at,
            chunk_id=result.chunk_id,
            chunk_index=result.chunk_index,
            chunking_version=result.chunking_version,
            text=result.text,
            text_hash=result.text_hash,
            start_offset=result.start_offset,
            end_offset=result.end_offset,
            embedding_model=result.embedding_model,
            embedding_version=result.embedding_version,
            index_schema_version=result.index_schema_version,
            metadata=dict(result.metadata),
        ),
        score=result.score,
    )


def search_documents_result_from_domain(
    results: Iterable[RetrievalResult],
) -> SearchDocumentsResult:
    return SearchDocumentsResult(
        results=tuple(retrieved_chunk_result_from_domain(result) for result in results)
    )


def signal_search_item_from_domain(
    result: SignalRetrievalResult,
) -> SignalSearchResultItem:
    signal = result.signal
    return SignalSearchResultItem(
        signal=RetrievedSignalResult(
            signal_id=signal.signal_id,
            tenant=signal.tenant,
            document_type=signal.document_type,
            document_id=signal.document_id,
            signal_type=signal.signal_type,
            signal_key=signal.signal_key,
            text=signal.text,
            source_version=signal.source_version,
            owner_kind=signal.owner_kind,
            folder_id=signal.folder_id,
            related_document_id=signal.related_document_id,
            evidence=tuple(
                RetrievedSignalEvidenceResult(
                    chunk_id=evidence.chunk_id,
                    quote=evidence.quote,
                    start_offset=evidence.start_offset,
                    end_offset=evidence.end_offset,
                    metadata=dict(evidence.metadata),
                )
                for evidence in signal.evidence
            ),
            confidence=signal.confidence,
            metadata=dict(signal.metadata),
        ),
        score=result.score,
    )


def search_signals_result_from_domain(
    results: Iterable[SignalRetrievalResult],
) -> SearchSignalsResult:
    return SearchSignalsResult(
        results=tuple(signal_search_item_from_domain(result) for result in results)
    )


def signal_search_item_to_domain(
    result: SignalSearchResultItem,
) -> SignalRetrievalResult:
    signal = result.signal
    return SignalRetrievalResult(
        signal=RetrievedSignal(
            signal_id=signal.signal_id,
            tenant=signal.tenant,
            document_type=signal.document_type,
            document_id=signal.document_id,
            signal_type=signal.signal_type,
            signal_key=signal.signal_key,
            text=signal.text,
            source_version=signal.source_version,
            owner_kind=signal.owner_kind,
            folder_id=signal.folder_id,
            related_document_id=signal.related_document_id,
            evidence=tuple(
                RetrievedSignalEvidence(
                    chunk_id=evidence.chunk_id,
                    quote=evidence.quote,
                    start_offset=evidence.start_offset,
                    end_offset=evidence.end_offset,
                    metadata=dict(evidence.metadata),
                )
                for evidence in signal.evidence
            ),
            confidence=signal.confidence,
            metadata=dict(signal.metadata),
        ),
        score=result.score,
    )


def signal_search_results_to_domain(
    result: SearchSignalsResult,
) -> list[SignalRetrievalResult]:
    return [signal_search_item_to_domain(item) for item in result.results]


def folder_search_item_from_domain(
    result: FolderRetrievalResult,
) -> FolderSearchResultItem:
    folder = result.folder
    return FolderSearchResultItem(
        folder=RetrievedFolderResult(
            tenant=folder.tenant,
            folder_id=folder.folder_id,
            source_version=folder.source_version,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
            name=folder.name,
            path=folder.path,
            description=folder.description,
        ),
        score=result.score,
        reason=result.reason,
    )


def search_folders_result_from_domain(
    results: Iterable[FolderRetrievalResult],
) -> SearchFoldersResult:
    return SearchFoldersResult(
        results=tuple(folder_search_item_from_domain(result) for result in results)
    )


def folder_search_item_to_domain(
    result: FolderSearchResultItem,
) -> FolderRetrievalResult:
    folder = result.folder
    return FolderRetrievalResult(
        folder=RetrievedFolder(
            tenant=folder.tenant,
            folder_id=folder.folder_id,
            source_version=folder.source_version,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
            name=folder.name,
            path=folder.path,
            description=folder.description,
        ),
        score=result.score,
        reason=result.reason,
    )


def folder_search_results_to_domain(
    result: SearchFoldersResult,
) -> list[FolderRetrievalResult]:
    return [folder_search_item_to_domain(item) for item in result.results]


def folder_recommendation_item_to_domain(
    item: FolderRecommendationResultItem,
) -> FolderRecommendation:
    return FolderRecommendation(
        folder_id=item.folder_id,
        reason=item.reason,
        score=item.score,
    )


def folder_recommendation_result_to_domain(
    result: RecommendFolderResult,
) -> FolderRecommendationResult:
    return FolderRecommendationResult(
        primary=folder_recommendation_item_to_domain(result.primary),
        alternatives=[
            folder_recommendation_item_to_domain(item)
            for item in result.alternatives
        ],
    )
