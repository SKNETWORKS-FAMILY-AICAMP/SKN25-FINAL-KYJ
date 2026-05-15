from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.domain.profiling.models import DocumentProfile, ProfileConcept
from foldmind_ai_core.domain.reference.documents import SourceDocument
from foldmind_ai_core.domain.reference.folders import SourceFolder
from foldmind_ai_core.shared.types import Metadata


@dataclass(frozen=True, slots=True)
class DocumentRelationshipProjection:
    tenant: str
    document_type: str
    document_id: str
    source_version: str
    folder_ids: tuple[str, ...] = ()
    tag_ids: tuple[str, ...] = ()

    @classmethod
    def from_source_document(
        cls,
        document: SourceDocument,
    ) -> DocumentRelationshipProjection:
        return cls(
            tenant=document.tenant,
            document_type=document.document_type,
            document_id=document.document_id,
            source_version=document.source_version,
            folder_ids=document.folder_ids,
            tag_ids=document.tag_ids,
        )


@dataclass(frozen=True, slots=True)
class DocumentConceptProjection:
    tenant: str
    document_type: str
    document_id: str
    source_version: str
    title: str
    profile_version: str
    concepts: tuple[ProfileConcept, ...] = ()
    profile_confidence: float | None = None
    metadata: Metadata = field(default_factory=dict)

    @classmethod
    def from_profile(cls, profile: DocumentProfile) -> DocumentConceptProjection:
        return cls(
            tenant=profile.tenant,
            document_type=profile.document_type,
            document_id=profile.document_id,
            source_version=profile.source_version,
            title=profile.title,
            profile_version=profile.profile_version,
            concepts=profile.concepts,
            profile_confidence=profile.profile_confidence,
            metadata={
                "model": profile.model,
                "prompt_version": profile.prompt_version,
                "profile_schema_version": profile.profile_schema_version,
            },
        )


@dataclass(frozen=True, slots=True)
class FolderRelationshipProjection:
    tenant: str
    folder_id: str
    source_version: str
    parent_folder_id: str | None = None

    @classmethod
    def from_source_folder(
        cls,
        folder: SourceFolder,
    ) -> FolderRelationshipProjection:
        return cls(
            tenant=folder.tenant,
            folder_id=folder.folder_id,
            source_version=folder.source_version,
            parent_folder_id=folder.parent_folder_id,
        )


@dataclass(frozen=True, slots=True)
class TagProjection:
    tenant: str
    tag_id: str
    label: str
    normalized_label: str
    source_version: str
    metadata: Metadata = field(default_factory=dict)
