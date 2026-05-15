from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.adapters.outbound.qdrant.client import (
    QdrantCollectionClient,
    validate_parallel,
)
from foldmind_ai_core.adapters.outbound.qdrant.filters import (
    document_identity_filter,
    document_scope_filter,
)
from foldmind_ai_core.adapters.outbound.qdrant.payloads import (
    chunk_from_payload,
    chunk_payload,
    payload_from_point,
)
from foldmind_ai_core.domain.indexing.chunks import DocumentChunk
from foldmind_ai_core.domain.retrieval.queries import SearchScope
from foldmind_ai_core.domain.retrieval.results import RetrievalResult
from foldmind_ai_core.shared.types import Vector
from foldmind_ai_core.shared.validation import InvalidInputError


@dataclass(slots=True)
class QdrantDocumentChunkVectorRepository:
    client: QdrantCollectionClient

    def replace_document_chunks(
        self,
        *,
        document_id: str,
        chunks: tuple[DocumentChunk, ...],
        vectors: tuple[Vector, ...],
    ) -> None:
        chunk_list = list(chunks)
        vector_list = list(vectors)
        validate_parallel(chunk_list, vector_list)
        if any(chunk.document_id != document_id for chunk in chunk_list):
            raise InvalidInputError("all chunks must belong to the replaced document_id.")
        self.delete_document_chunks(document_id=document_id)
        self.client.upsert_points(
            [
                self.client.point(
                    key=chunk.chunk_id,
                    vector=vector,
                    payload=chunk_payload(chunk),
                )
                for chunk, vector in zip(chunk_list, vector_list, strict=True)
            ]
        )

    def delete_document_chunks(
        self,
        *,
        document_id: str,
    ) -> None:
        self.client.delete_by_filter(
            document_identity_filter(
                self.client,
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
            chunk = chunk_from_payload(payload_from_point(point))
            if not chunk.document_id.strip():
                continue
            results.append(
                RetrievalResult(
                    chunk=chunk,
                    score=float(getattr(point, "score", 0.0)),
                )
            )
        return results
