from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from qdrant_client import QdrantClient, models

from foldmind_ai_core.adapters.outbound.qdrant.settings import QdrantSettings
from foldmind_ai_core.core.application.queries.retrieval import TimestampRange
from foldmind_ai_core.shared.internal_ids import stable_internal_id
from foldmind_ai_core.shared.types import JsonObject, Metadata, Vector
from foldmind_ai_core.shared.validation import InvalidInputError, require_non_blank


@dataclass(slots=True)
class QdrantCollectionConfig:
    collection_name: str
    vector_size: int
    distance: str = "Cosine"
    payload_indexes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self.collection_name = require_non_blank(
            self.collection_name,
            "collection_name",
        )
        if (
            isinstance(self.vector_size, bool)
            or not isinstance(self.vector_size, int)
            or self.vector_size <= 0
        ):
            raise InvalidInputError("vector_size must be a positive integer.")
        self.distance = require_non_blank(self.distance, "distance")
        payload_indexes: list[str] = []
        for field_name in self.payload_indexes:
            if not isinstance(field_name, str):
                raise InvalidInputError(
                    "payload_indexes must contain non-blank strings."
                )
            payload_indexes.append(require_non_blank(field_name, "payload_indexes"))
        self.payload_indexes = tuple(payload_indexes)


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

    @property
    def collection_name(self) -> str:
        return self.config.collection_name

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
            exists = self._client.collection_exists(self.config.collection_name)
            if not isinstance(exists, bool):
                raise InvalidInputError("collection_exists must return a boolean.")
            return exists
        try:
            self._client.get_collection(self.config.collection_name)
        except Exception:
            return False
        return True

    def _distance(self) -> Any:
        distance = self.config.distance.upper()
        try:
            return getattr(self._models.Distance, distance)
        except AttributeError as exc:
            raise InvalidInputError(
                f"Unsupported Qdrant distance: {self.config.distance}."
            ) from exc

    def _ensure_payload_indexes(self) -> None:
        if not hasattr(self._client, "create_payload_index"):
            return
        for field_name in self.config.payload_indexes:
            schema = self._payload_schema(field_name)
            self._client.create_payload_index(
                collection_name=self.config.collection_name,
                field_name=field_name,
                field_schema=schema,
            )

    def _payload_schema(self, field_name: str) -> Any:
        if field_name in {"created_at", "updated_at"} and hasattr(
            self._models.PayloadSchemaType,
            "DATETIME",
        ):
            return self._models.PayloadSchemaType.DATETIME
        return self._models.PayloadSchemaType.KEYWORD

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
        validate_vector(query_vector)
        validate_top_k(top_k)
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

    def point(
        self,
        *,
        key: str,
        vector: Vector,
        payload: JsonObject,
        point_id: str | None = None,
    ) -> Any:
        if len(vector) != self.config.vector_size:
            raise InvalidInputError(
                f"Expected vector size {self.config.vector_size}, got {len(vector)}."
            )
        validate_vector(vector)
        return self._models.PointStruct(
            id=point_id or stable_internal_id(
                "qdrant-point",
                self.config.collection_name,
                key,
            ),
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
        owner_kind: str | None = None,
        signal_type: str | None = None,
        created_at: TimestampRange | None = None,
        updated_at: TimestampRange | None = None,
        metadata_filter: Metadata | None = None,
    ) -> Any:
        must = []
        if tenant is not None:
            must.append(self._match_value_condition("tenant", tenant))
        for field_name, value in (
            ("document_type", document_type),
            ("document_id", document_id),
            ("folder_id", folder_id),
            ("owner_kind", owner_kind),
            ("signal_type", signal_type),
        ):
            if value is not None:
                must.append(self._match_value_condition(field_name, value))
        for field_name, values in (
            ("document_id", document_ids),
            ("folder_id", folder_ids),
        ):
            if values:
                must.append(
                    self._models.FieldCondition(
                        key=field_name,
                        match=self._models.MatchAny(any=list(values)),
                    )
                )
        for field_name, timestamp_range in (
            ("created_at", created_at),
            ("updated_at", updated_at),
        ):
            if timestamp_range is not None:
                must.append(self._range_condition(field_name, timestamp_range))
        for key, metadata_value in (metadata_filter or {}).items():
            must.append(self._match_value_condition(f"metadata.{key}", metadata_value))
        return self._models.Filter(must=must)

    def _match_value_condition(self, field_name: str, value: object) -> Any:
        return self._models.FieldCondition(
            key=field_name,
            match=self._models.MatchValue(value=value),
        )

    def _range_condition(self, field_name: str, timestamp_range: TimestampRange) -> Any:
        range_values = {
            key: value
            for key in ("gt", "gte", "lt", "lte")
            if (value := getattr(timestamp_range, key)) is not None
        }
        if hasattr(self._models, "DatetimeRange"):
            return self._models.FieldCondition(
                key=field_name,
                datetime_range=self._models.DatetimeRange(**range_values),
            )
        return self._models.FieldCondition(
            key=field_name,
            range=self._models.Range(**range_values),
        )


def validate_parallel(items: Sequence[object], vectors: Sequence[Vector]) -> None:
    if len(items) != len(vectors):
        raise InvalidInputError("items and vectors must have the same length.")


def validate_vector(vector: Vector) -> None:
    for coordinate in vector:
        if isinstance(coordinate, bool) or not isinstance(coordinate, int | float):
            raise InvalidInputError("vector must contain numbers.")
        if not math.isfinite(float(coordinate)):
            raise InvalidInputError("vector must contain finite numbers.")


def validate_top_k(top_k: int) -> None:
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
        raise InvalidInputError("top_k must be a positive integer.")
