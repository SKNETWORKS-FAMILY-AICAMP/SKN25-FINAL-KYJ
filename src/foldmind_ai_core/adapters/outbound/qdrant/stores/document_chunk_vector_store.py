from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.adapters.outbound.qdrant.client import (
    QdrantCollectionClient,
    validate_parallel,
)
from foldmind_ai_core.adapters.outbound.qdrant.filters import document_scope_filter
from foldmind_ai_core.adapters.outbound.qdrant.mappers import (
    chunk_from_payload,
    chunk_payload,
    payload_from_point,
    score_from_point,
)
from foldmind_ai_core.core.application.ports.outbound.vector_store import VectorWriteResult
from foldmind_ai_core.core.application.projections.vector import DocumentChunkVectorProjection
from foldmind_ai_core.core.application.queries.retrieval import SearchScope
from foldmind_ai_core.core.application.queries.scope_matching import (
    sort_by_timestamp_scope,
)
from foldmind_ai_core.core.domain.models.retrieval.results import RetrievalResult
from foldmind_ai_core.shared.canonical_json import json_digest
from foldmind_ai_core.shared.types import Vector
from foldmind_ai_core.shared.validation import InvalidInputError


@dataclass(slots=True)
class QdrantDocumentChunkVectorStore:
    client: QdrantCollectionClient

    def replace_document_chunks(
        self,
        *,
        tenant: str,
        document_id: str,
        chunks: tuple[DocumentChunkVectorProjection, ...],
        vectors: tuple[Vector, ...],
    ) -> tuple[VectorWriteResult, ...]:
        validate_parallel(chunks, vectors)
        if any(
            chunk.tenant != tenant
            or chunk.document_id != document_id
            for chunk in chunks
        ):
            raise InvalidInputError("all chunks must belong to the replaced document_id.")
        payloads = tuple(chunk_payload(chunk) for chunk in chunks)
        points = [
            self.client.point(
                key=chunk.chunk_id,
                vector=vector,
                payload=payload,
            )
            for chunk, vector, payload in zip(chunks, vectors, payloads, strict=True)
        ]
        self.delete_document_chunks(
            document_id=document_id,
        )
        self.client.upsert_points(points)
        return tuple(
            VectorWriteResult(
                collection_name=self.client.collection_name,
                point_id=str(point.id),
                payload_digest=json_digest(payload),
            )
            for point, payload in zip(points, payloads, strict=True)
        )

    def delete_document_chunks(
        self,
        *,
        document_id: str,
    ) -> None:
        self.client.delete_by_filter(
            self.client.filter(
                document_id=document_id,
            )
        )

    def search_chunks(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[RetrievalResult]:
        points = self.client.search_points(
            query_vector=query_vector,
            top_k=top_k,
            qdrant_filter=document_scope_filter(self.client, tenant=tenant, scope=scope),
        )
        results: list[RetrievalResult] = []
        for point in points:
            score = score_from_point(point)
            if score is None:
                continue
            try:
                chunk = chunk_from_payload(payload_from_point(point))
            except (KeyError, TypeError, ValueError):
                continue
            results.append(
                RetrievalResult(
                    chunk=chunk,
                    score=score,
                )
            )
        return sort_by_timestamp_scope(
            results,
            scope=scope,
            timestamp_value=lambda result, field: getattr(result.chunk, field),
        )
