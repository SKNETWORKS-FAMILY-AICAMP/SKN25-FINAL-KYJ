from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.adapters.outbound.qdrant.client import (
    QdrantCollectionClient,
    validate_parallel,
)
from foldmind_ai_core.adapters.outbound.qdrant.filters import signal_scope_filter
from foldmind_ai_core.adapters.outbound.qdrant.mappers import (
    payload_from_point,
    score_from_point,
    signal_from_payload,
    signal_payload,
)
from foldmind_ai_core.core.application.ports.outbound.vector_store import VectorWriteResult
from foldmind_ai_core.core.application.projections.vector import (
    DocumentSignalVectorProjection,
    FolderSignalVectorProjection,
)
from foldmind_ai_core.core.application.queries.retrieval import SearchScope
from foldmind_ai_core.core.domain.models.retrieval.results import SignalRetrievalResult
from foldmind_ai_core.shared.canonical_json import json_digest
from foldmind_ai_core.shared.internal_ids import stable_internal_id
from foldmind_ai_core.shared.types import Vector
from foldmind_ai_core.shared.validation import InvalidInputError


@dataclass(slots=True)
class QdrantSignalVectorStore:
    client: QdrantCollectionClient

    def replace_document_signals(
        self,
        *,
        tenant: str,
        document_id: str,
        signals: tuple[DocumentSignalVectorProjection, ...],
        vectors: tuple[Vector, ...],
    ) -> tuple[VectorWriteResult, ...]:
        validate_parallel(signals, vectors)
        if any(
            signal.tenant != tenant
            or signal.document_id != document_id
            for signal in signals
        ):
            raise InvalidInputError(
                "all signals must belong to the replaced document_id."
            )
        self.delete_document_signals(
            document_id=document_id,
        )
        return self._upsert_signals(
            signals=signals,
            vectors=vectors,
            owner_kind="document",
        )

    def delete_document_signals(
        self,
        *,
        document_id: str,
    ) -> None:
        self.client.delete_by_filter(
            self.client.filter(
                owner_kind="document",
                document_id=document_id,
            )
        )

    def replace_folder_signals(
        self,
        *,
        tenant: str,
        folder_id: str,
        signals: tuple[FolderSignalVectorProjection, ...],
        vectors: tuple[Vector, ...],
    ) -> tuple[VectorWriteResult, ...]:
        validate_parallel(signals, vectors)
        if any(
            signal.tenant != tenant
            or signal.folder_id != folder_id
            for signal in signals
        ):
            raise InvalidInputError("all signals must belong to the replaced folder_id.")
        self.delete_folder_signals(folder_id=folder_id)
        return self._upsert_signals(
            signals=signals,
            vectors=vectors,
            owner_kind="folder",
        )

    def delete_folder_signals(
        self,
        *,
        folder_id: str,
    ) -> None:
        self.client.delete_by_filter(
            self.client.filter(
                owner_kind="folder",
                folder_id=folder_id,
            )
        )

    def delete_stale_folder_signals(
        self,
        *,
        folder_id: str,
        current_index_input_digest: str,
    ) -> None:
        self.client.delete_by_filter(
            self.client._models.Filter(
                must=[
                    self.client._match_value_condition("owner_kind", "folder"),
                    self.client._match_value_condition("folder_id", folder_id),
                ],
                must_not=[
                    self.client._match_value_condition(
                        "index_input_digest",
                        current_index_input_digest,
                    )
                ],
            )
        )

    def search_signals(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        signal_type: str | None = None,
        scope: SearchScope | None = None,
    ) -> list[SignalRetrievalResult]:
        points = self.client.search_points(
            query_vector=query_vector,
            top_k=top_k,
            qdrant_filter=signal_scope_filter(
                self.client,
                tenant=tenant,
                signal_type=signal_type,
                scope=scope,
            ),
        )
        results: list[SignalRetrievalResult] = []
        for point in points:
            score = score_from_point(point)
            if score is None:
                continue
            try:
                signal = signal_from_payload(payload_from_point(point))
            except (KeyError, TypeError, ValueError):
                continue
            results.append(SignalRetrievalResult(signal=signal, score=score))
        return results

    def _upsert_signals(
        self,
        *,
        signals: tuple[
            DocumentSignalVectorProjection | FolderSignalVectorProjection,
            ...,
        ],
        vectors: tuple[Vector, ...],
        owner_kind: str,
    ) -> tuple[VectorWriteResult, ...]:
        payloads = tuple(signal_payload(signal) for signal in signals)
        points = [
            self.client.point(
                key=signal.signal_id,
                vector=vector,
                payload=payload,
                point_id=_signal_point_id(
                    collection_name=self.client.collection_name,
                    owner_kind=owner_kind,
                    owner_id=_signal_owner_id(signal),
                    signal_id=signal.signal_id,
                    index_input_digest=signal.index_input_digest,
                ),
            )
            for signal, vector, payload in zip(signals, vectors, payloads, strict=True)
        ]
        self.client.upsert_points(points)
        return tuple(
            VectorWriteResult(
                collection_name=self.client.collection_name,
                point_id=str(point.id),
                payload_digest=json_digest(payload),
            )
            for point, payload in zip(points, payloads, strict=True)
        )


def _signal_owner_id(
    signal: DocumentSignalVectorProjection | FolderSignalVectorProjection,
) -> str:
    if isinstance(signal, DocumentSignalVectorProjection):
        return signal.document_id
    return signal.folder_id


def _signal_point_id(
    *,
    collection_name: str,
    owner_kind: str,
    owner_id: str,
    signal_id: str,
    index_input_digest: str,
) -> str:
    return stable_internal_id(
        collection_name,
        "signal-vector",
        owner_kind,
        owner_id,
        signal_id,
        index_input_digest,
    )
