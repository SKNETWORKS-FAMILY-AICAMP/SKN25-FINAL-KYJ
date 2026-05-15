from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.adapters.outbound.qdrant.client import (
    QdrantCollectionClient,
    validate_parallel,
)
from foldmind_ai_core.adapters.outbound.qdrant.filters import (
    folder_identity_filter,
    folder_scope_filter,
)
from foldmind_ai_core.adapters.outbound.qdrant.payloads import (
    folder_from_payload,
    folder_payload,
    payload_from_point,
)
from foldmind_ai_core.domain.reference.folders import FolderVectorProjection
from foldmind_ai_core.domain.retrieval.queries import SearchScope
from foldmind_ai_core.domain.retrieval.results import FolderRetrievalResult
from foldmind_ai_core.shared.types import Vector


@dataclass(slots=True)
class QdrantFolderVectorRepository:
    client: QdrantCollectionClient

    def upsert_folder_vector(
        self,
        *,
        projection: FolderVectorProjection,
        vector: Vector,
    ) -> None:
        validate_parallel([projection], [vector])
        self.delete_folder_vector(folder_id=projection.folder_id)
        self.client.upsert_points(
            [
                self.client.point(
                    key=projection.folder_id,
                    vector=vector,
                    payload=folder_payload(projection),
                )
            ]
        )

    def delete_folder_vector(self, *, folder_id: str) -> None:
        self.client.delete_by_filter(
            folder_identity_filter(self.client, folder_id=folder_id)
        )

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
            folder = folder_from_payload(payload_from_point(point))
            if not folder.folder_id.strip():
                continue
            results.append(
                FolderRetrievalResult(
                    folder=folder,
                    score=float(getattr(point, "score", 0.0)),
                    reason="Folder metadata is semantically close to the query.",
                )
            )
        return results
