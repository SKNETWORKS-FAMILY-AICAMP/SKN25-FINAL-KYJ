from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from foldmind_ai_core.domain.profiling.models import DocumentProfile
from foldmind_ai_core.shared.types import Metadata


@dataclass(frozen=True, slots=True)
class SourceDocument:
    tenant: str
    document_type: str
    document_id: str
    source_version: str
    title: str
    body: str
    folder_ids: tuple[str, ...] = ()
    tag_ids: tuple[str, ...] = ()
    metadata: Metadata = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        if self.title.strip():
            return f"{self.title}\n\n{self.body}".strip()
        return self.body.strip()


@dataclass(frozen=True, slots=True)
class DocumentVectorProjection:
    tenant: str
    document_type: str
    document_id: str
    source_version: str
    profile_version: str
    profile_schema_version: str
    embedding_input: str
    embedding_input_hash: str
    embedding_model: str
    embedding_version: str
    index_schema_version: str
    concept_ids: tuple[str, ...] = ()
    profile_confidence: float | None = None

    @classmethod
    def from_profile(
        cls,
        profile: DocumentProfile,
        *,
        embedding_model: str,
        embedding_version: str,
        index_schema_version: str,
    ) -> DocumentVectorProjection:
        embedding_input = _document_embedding_input(profile)
        return cls(
            tenant=profile.tenant,
            document_type=profile.document_type,
            document_id=profile.document_id,
            source_version=profile.source_version,
            profile_version=profile.profile_version,
            profile_schema_version=profile.profile_schema_version,
            concept_ids=tuple(concept.concept_id for concept in profile.concepts),
            profile_confidence=profile.profile_confidence,
            embedding_input=embedding_input,
            embedding_input_hash=_hash_text(embedding_input),
            embedding_model=embedding_model,
            embedding_version=embedding_version,
            index_schema_version=index_schema_version,
        )


def _document_embedding_input(profile: DocumentProfile) -> str:
    parts = [
        profile.title,
        profile.summary,
        " ".join(concept.label for concept in profile.concepts),
    ]
    return "\n\n".join(part.strip() for part in parts if part.strip())

def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()