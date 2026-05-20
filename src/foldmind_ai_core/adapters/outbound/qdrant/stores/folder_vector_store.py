from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.adapters.outbound.qdrant.client import QdrantCollectionClient
from foldmind_ai_core.adapters.outbound.qdrant.filters import folder_scope_filter
from foldmind_ai_core.adapters.outbound.qdrant.mappers import (
    folder_from_payload,
    folder_payload,
    payload_from_point,
    score_from_point,
)
from foldmind_ai_core.core.application.ports.outbound.vector_store import VectorWriteResult
from foldmind_ai_core.core.application.projections.vector import FolderVectorProjection
from foldmind_ai_core.core.application.queries.retrieval import SearchScope
from foldmind_ai_core.core.application.queries.scope_matching import (
    sort_by_timestamp_scope,
)
from foldmind_ai_core.core.domain.models.retrieval.results import FolderRetrievalResult
from foldmind_ai_core.shared.canonical_json import json_digest
from foldmind_ai_core.shared.internal_ids import stable_internal_id
from foldmind_ai_core.shared.types import Vector


@dataclass(slots=True)
class QdrantFolderVectorStore:
    client: QdrantCollectionClient

    def upsert_folder_vector(
        self,
        *,
        projection: FolderVectorProjection,
        vector: Vector,
    ) -> VectorWriteResult:
        payload = folder_payload(projection)
        point = self.client.point(
            key=projection.folder_id,
            vector=vector,
            payload=payload,
            point_id=stable_internal_id(
                self.client.collection_name,
                "folder",
                projection.folder_id,
                projection.index_input_digest,
            ),
        )
        self.delete_folder_vector(folder_id=projection.folder_id)
        self.client.upsert_points([point])
        return VectorWriteResult(
            collection_name=self.client.collection_name,
            point_id=str(point.id),
            payload_digest=json_digest(payload),
        )

    def delete_folder_vector(self, *, folder_id: str) -> None:
        self.client.delete_by_filter(self.client.filter(folder_id=folder_id))

    def search_folders(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[FolderRetrievalResult]:
        points = self.client.search_points(
            query_vector=query_vector,
            top_k=top_k,
            qdrant_filter=folder_scope_filter(self.client, tenant=tenant, scope=scope),
        )
        results: list[FolderRetrievalResult] = []
        for point in points:
            score = score_from_point(point)
            if score is None:
                continue
            try:
                folder = folder_from_payload(payload_from_point(point))
            except (KeyError, TypeError, ValueError):
                continue
            results.append(
                FolderRetrievalResult(
                    folder=folder,
                    score=score,
                    reason="Folder metadata is semantically close to the query.",
                )
            )
        return sort_by_timestamp_scope(
            results,
            scope=scope,
            timestamp_value=lambda result, field: getattr(result.folder, field),
        )
