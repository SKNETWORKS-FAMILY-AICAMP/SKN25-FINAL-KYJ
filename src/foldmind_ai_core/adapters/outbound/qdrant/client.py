from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from qdrant_client import QdrantClient, models

from foldmind_ai_core.adapters.outbound.qdrant.settings import QdrantSettings
from foldmind_ai_core.shared.types import Metadata, Vector
from foldmind_ai_core.shared.validation import InvalidInputError


@dataclass(slots=True)
class QdrantCollectionConfig:
    collection_name: str
    vector_size: int
    distance: str = "Cosine"
    payload_indexes: tuple[str, ...] = ()


@dataclass(slots=True)
class QdrantCollectionClient:
    config: QdrantCollectionConfig
    settings: QdrantSettings
    client: Any | None = None
    _models: Any = field(init=False, repr=False)
    _client: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._models = models
        self._client = self.client or QdrantClient(
            url=self.settings.url,
            api_key=self.settings.api_key,
        )

    def setup_collection(self) -> None:
        self._ensure_collection()
        self._ensure_payload_indexes()

    def _ensure_collection(self) -> None:
        if self._collection_exists():
            return
        self._client.create_collection(
            collection_name=self.config.collection_name,
            vectors_config=self._models.VectorParams(
                size=self.config.vector_size,
                distance=self._distance(),
            ),
        )

    def _collection_exists(self) -> bool:
        if hasattr(self._client, "collection_exists"):
            return bool(self._client.collection_exists(self.config.collection_name))
        try:
            self._client.get_collection(self.config.collection_name)
        except Exception:
            return False
        return True

    def _distance(self) -> Any:
        distance = self.config.distance.upper()
        return getattr(self._models.Distance, distance)

    def _ensure_payload_indexes(self) -> None:
        if not hasattr(self._client, "create_payload_index"):
            return
        schema = getattr(self._models.PayloadSchemaType, "KEYWORD")
        for field_name in self.config.payload_indexes:
            self._client.create_payload_index(
                collection_name=self.config.collection_name,
                field_name=field_name,
                field_schema=schema,
            )

    def upsert_points(self, points: list[Any]) -> None:
        if points:
            self._client.upsert(collection_name=self.config.collection_name, points=points)

    def delete_by_filter(self, qdrant_filter: Any) -> None:
        self._client.delete(
            collection_name=self.config.collection_name,
            points_selector=self._models.FilterSelector(filter=qdrant_filter),
        )

    def search_points(
        self,
        *,
        query_vector: Vector,
        top_k: int,
        qdrant_filter: Any,
    ) -> list[Any]:
        if hasattr(self._client, "query_points"):
            response = self._client.query_points(
                collection_name=self.config.collection_name,
                query=query_vector,
                query_filter=qdrant_filter,
                limit=top_k,
                with_payload=True,
            )
            return list(getattr(response, "points", response))
        return list(
            self._client.search(
                collection_name=self.config.collection_name,
                query_vector=query_vector,
                query_filter=qdrant_filter,
                limit=top_k,
                with_payload=True,
            )
        )

    def point(self, *, key: str, vector: Vector, payload: Metadata) -> Any:
        if len(vector) != self.config.vector_size:
            raise InvalidInputError(
                f"Expected vector size {self.config.vector_size}, got {len(vector)}."
            )
        return self._models.PointStruct(
            id=key,
            vector=vector,
            payload=payload,
        )

    def filter(
        self,
        *,
        tenant: str | None = None,
        document_type: str | None = None,
        document_id: str | None = None,
        document_ids: tuple[str, ...] = (),
        folder_id: str | None = None,
        folder_ids: tuple[str, ...] = (),
        metadata_filter: Metadata | None = None,
    ) -> Any:
        must = []
        if tenant is not None:
            must.append(self._match_value_condition("tenant", tenant))
        must.extend(
            self._optional_match_conditions(
                (
                    ("document_type", document_type),
                    ("document_id", document_id),
                    ("folder_id", folder_id),
                )
            )
        )
        must.extend(
            self._optional_match_any_conditions(
                (
                    ("document_id", document_ids),
                    ("folder_id", folder_ids),
                )
            )
        )
        must.extend(self._metadata_conditions(metadata_filter or {}))
        return self._models.Filter(must=must)

    def _optional_match_conditions(
        self,
        values: tuple[tuple[str, object | None], ...],
    ) -> list[Any]:
        return [
            self._match_value_condition(field_name, value)
            for field_name, value in values
            if value is not None
        ]

    def _optional_match_any_conditions(
        self,
        values: tuple[tuple[str, tuple[str, ...]], ...],
    ) -> list[Any]:
        return [
            self._match_any_condition(field_name, field_values)
            for field_name, field_values in values
            if field_values
        ]

    def _metadata_conditions(self, metadata_filter: Metadata) -> list[Any]:
        return [
            self._match_value_condition(f"metadata.{key}", value)
            for key, value in metadata_filter.items()
        ]

    def _match_value_condition(self, field_name: str, value: object) -> Any:
        return self._models.FieldCondition(
            key=field_name,
            match=self._models.MatchValue(value=value),
        )

    def _match_any_condition(self, field_name: str, values: tuple[str, ...]) -> Any:
        return self._models.FieldCondition(
            key=field_name,
            match=self._models.MatchAny(any=list(values)),
        )


def validate_parallel(items: list[object], vectors: list[Vector]) -> None:
    if len(items) != len(vectors):
        raise InvalidInputError("items and vectors must have the same length.")
