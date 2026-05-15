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
    document_from_payload,
    document_payload,
    payload_from_point,
)
from foldmind_ai_core.domain.reference.documents import DocumentVectorProjection
from foldmind_ai_core.domain.retrieval.queries import SearchScope
from foldmind_ai_core.domain.retrieval.results import DocumentRetrievalResult
from foldmind_ai_core.shared.types import Vector


@dataclass(slots=True)
class QdrantDocumentVectorRepository:
    client: QdrantCollectionClient

    def upsert_document_vector(
        self,
        *,
        projection: DocumentVectorProjection,
        vector: Vector,
    ) -> None:
        validate_parallel([projection], [vector])
        self.delete_document_vector(
            document_id=projection.document_id,
        )
        self.client.upsert_points(
            [
                self.client.point(
                    key=projection.document_id,
                    vector=vector,
                    payload=document_payload(projection),
                )
            ]
        )

    def delete_document_vector(
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

    def search_documents(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[DocumentRetrievalResult]:
        points = self.client.search_points(
            query_vector=query_vector,
            top_k=top_k,
            qdrant_filter=document_scope_filter(self.client, tenant=tenant, scope=scope),
        )
        results: list[DocumentRetrievalResult] = []
        for point in points:
            document = document_from_payload(payload_from_point(point))
            if not document.document_id.strip():
                continue
            results.append(
                DocumentRetrievalResult(
                    document=document,
                    score=float(getattr(point, "score", 0.0)),
                )
            )
        return results
