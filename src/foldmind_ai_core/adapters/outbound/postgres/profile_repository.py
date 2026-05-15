from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from foldmind_ai_core.adapters.outbound.postgres.client import (
    PostgresClient,
    jsonb,
    row_value,
)
from foldmind_ai_core.domain.profiling.models import DocumentProfile, ProfileConcept
from foldmind_ai_core.shared.types import Metadata

_UPSERT_DOCUMENT_PROFILE_SQL = """
INSERT INTO document_profiles (
    document_id,
    tenant,
    document_type,
    source_version,
    profile_version,
    profile_schema_version,
    title,
    summary,
    concepts_json,
    profile_confidence,
    model,
    prompt_version,
    metadata,
    updated_at
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
ON CONFLICT (document_id)
DO UPDATE SET
    tenant = EXCLUDED.tenant,
    document_type = EXCLUDED.document_type,
    source_version = EXCLUDED.source_version,
    profile_version = EXCLUDED.profile_version,
    profile_schema_version = EXCLUDED.profile_schema_version,
    title = EXCLUDED.title,
    summary = EXCLUDED.summary,
    concepts_json = EXCLUDED.concepts_json,
    profile_confidence = EXCLUDED.profile_confidence,
    model = EXCLUDED.model,
    prompt_version = EXCLUDED.prompt_version,
    metadata = EXCLUDED.metadata,
    updated_at = now()
"""

_GET_DOCUMENT_PROFILE_SQL = """
SELECT
    tenant,
    document_type,
    document_id,
    source_version,
    profile_version,
    profile_schema_version,
    title,
    summary,
    concepts_json,
    profile_confidence,
    model,
    prompt_version,
    metadata
FROM document_profiles
WHERE document_id = %s
"""

_DELETE_DOCUMENT_PROFILE_SQL = """
DELETE FROM document_profiles
WHERE document_id = %s
"""


@dataclass(slots=True)
class PostgresProfileRepository:
    client: PostgresClient

    def upsert(self, profile: DocumentProfile) -> None:
        with self.client.connect() as conn:
            self.upsert_with_connection(conn, profile)

    def upsert_with_connection(self, conn: Any, profile: DocumentProfile) -> None:
        conn.execute(
            _UPSERT_DOCUMENT_PROFILE_SQL,
            (
                profile.document_id,
                profile.tenant,
                profile.document_type,
                profile.source_version,
                profile.profile_version,
                profile.profile_schema_version,
                profile.title,
                profile.summary,
                jsonb(_concepts_json(profile.concepts)),
                profile.profile_confidence,
                profile.model,
                profile.prompt_version,
                jsonb(profile.metadata),
            ),
        )

    def get_document_profile(
        self,
        *,
        document_id: str,
    ) -> DocumentProfile | None:
        with self.client.connect() as conn:
            row = conn.execute(
                _GET_DOCUMENT_PROFILE_SQL,
                (document_id,),
            ).fetchone()
            if row is None:
                return None
            return _document_profile_from_row(row)

    def delete_document_profile(
        self,
        *,
        document_id: str,
    ) -> None:
        with self.client.connect() as conn:
            self.delete_with_connection(conn, document_id=document_id)

    def delete_with_connection(self, conn: Any, *, document_id: str) -> None:
        conn.execute(_DELETE_DOCUMENT_PROFILE_SQL, (document_id,))


def _document_profile_from_row(row: Any) -> DocumentProfile:
    return DocumentProfile(
        tenant=_str(row, "tenant", 0),
        document_type=_str(row, "document_type", 1),
        document_id=_str(row, "document_id", 2),
        source_version=_str(row, "source_version", 3),
        profile_version=_str(row, "profile_version", 4),
        profile_schema_version=_str(row, "profile_schema_version", 5),
        title=_str(row, "title", 6),
        summary=_str(row, "summary", 7),
        concepts=_concepts_from_json(row_value(row, "concepts_json", 8)),
        profile_confidence=_optional_float(row, "profile_confidence", 9),
        model=_str(row, "model", 10),
        prompt_version=_str(row, "prompt_version", 11),
        metadata=_metadata(row_value(row, "metadata", 12)),
    )


def _concepts_json(concepts: tuple[ProfileConcept, ...]) -> list[dict[str, Any]]:
    return [
        {
            "concept_id": concept.concept_id,
            "concept_key": concept.concept_key,
            "label": concept.label,
            "confidence": concept.confidence,
            "evidence_chunk_ids": list(concept.evidence_chunk_ids),
            "metadata": concept.metadata,
        }
        for concept in concepts
    ]


def _concepts_from_json(value: object) -> tuple[ProfileConcept, ...]:
    if not isinstance(value, list | tuple):
        return ()
    concepts: list[ProfileConcept] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        concepts.append(
            ProfileConcept(
                concept_id=str(item.get("concept_id") or ""),
                concept_key=str(item.get("concept_key") or ""),
                label=str(item.get("label") or ""),
                confidence=(
                    float(item["confidence"])
                    if item.get("confidence") is not None
                    else None
                ),
                evidence_chunk_ids=tuple(
                    str(chunk_id)
                    for chunk_id in item.get("evidence_chunk_ids", ())
                    if str(chunk_id).strip()
                ),
                metadata=_metadata(item.get("metadata")),
            )
        )
    return tuple(concepts)


def _metadata(value: object) -> Metadata:
    return cast(Metadata, value if isinstance(value, dict) else {})


def _str(row: Any, key: str, index: int) -> str:
    return str(row_value(row, key, index) or "")


def _optional_float(row: Any, key: str, index: int) -> float | None:
    value = row_value(row, key, index)
    return float(value) if value is not None else None
