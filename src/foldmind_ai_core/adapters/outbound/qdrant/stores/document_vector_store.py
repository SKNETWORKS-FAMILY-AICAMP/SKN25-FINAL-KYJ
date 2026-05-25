from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.adapters.outbound.qdrant.client import QdrantCollectionClient
from foldmind_ai_core.adapters.outbound.qdrant.filters import document_scope_filter
from foldmind_ai_core.adapters.outbound.qdrant.mappers import (
    document_from_payload,
    document_payload,
    payload_from_point,
    score_from_point,
)
from foldmind_ai_core.core.application.models.vector_projection import (
    DocumentVectorProjection,
    VectorWriteResult,
)
from foldmind_ai_core.core.application.models.search import SearchScope
from foldmind_ai_core.core.application.models.retrieval import DocumentRetrievalResult
from foldmind_ai_core.core.application.search_scope import (
    sort_by_timestamp_scope,
)
from foldmind_ai_core.shared.canonical_json import json_digest
from foldmind_ai_core.shared.internal_ids import stable_internal_id
from foldmind_ai_core.shared.types import Vector


@dataclass(slots=True)
class QdrantDocumentVectorStore:
    client: QdrantCollectionClient

    def upsert_document_vector(
        self,
        *,
        projection: DocumentVectorProjection,
        vector: Vector,
    ) -> VectorWriteResult:
        payload = document_payload(projection)
        point = self.client.point(
            key=projection.document_id,
            vector=vector,
            payload=payload,
            point_id=stable_internal_id(
                self.client.collection_name,
                "document",
                projection.tenant,
                projection.document_id,
                projection.vector_input_digest,
            ),
        )
        self.delete_document_vector(
            tenant=projection.tenant,
            document_id=projection.document_id,
        )
        self.client.upsert_points([point])
        return VectorWriteResult(
            collection_name=self.client.collection_name,
            point_id=str(point.id),
            payload_digest=json_digest(payload),
        )

    def delete_document_vector(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        self.client.delete_by_filter(
            self.client.filter(
                tenant=tenant,
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
            score = score_from_point(point)
            if score is None:
                continue
            try:
                document = document_from_payload(payload_from_point(point))
            except (KeyError, TypeError, ValueError):
                continue
            results.append(
                DocumentRetrievalResult(
                    document=document,
                    score=score,
                )
            )
        return sort_by_timestamp_scope(
            results,
            scope=scope,
            timestamp_value=lambda result, field: getattr(result.document, field),
        )
