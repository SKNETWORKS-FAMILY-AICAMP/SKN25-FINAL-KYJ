from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.shared.types import Metadata


@dataclass(frozen=True, slots=True)
class ProfileConcept:
    concept_id: str
    concept_key: str
    label: str
    confidence: float | None = None
    evidence_chunk_ids: tuple[str, ...] = ()
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DocumentProfile:
    tenant: str
    document_type: str
    document_id: str
    source_version: str
    title: str
    summary: str
    profile_version: str
    profile_schema_version: str
    concepts: tuple[ProfileConcept, ...] = ()
    profile_confidence: float | None = None
    model: str = ""
    prompt_version: str = ""
    metadata: Metadata = field(default_factory=dict)
