from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypeAlias

from foldmind_ai_core.core.domain.services.workflow import (
    validate_host_action_attempts,
    validate_host_action_policy,
)
from foldmind_ai_core.shared.internal_ids import new_internal_id
from foldmind_ai_core.shared.types import Metadata


class HostActionType(StrEnum):
    CREATE_FOLDER = "create_folder"
    CREATE_DOCUMENT = "create_document"
    UPDATE_DOCUMENT = "update_document"
    MOVE_DOCUMENT = "move_document"
    LINK_DOCUMENTS = "link_documents"


class HostActionStatus(StrEnum):
    PROPOSED = "proposed"
    READY = "ready"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class HostActionResultType(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRY = "retry"
    SKIPPED = "skipped"


@dataclass(slots=True)
class HostActionPolicy:
    max_attempts: int = 1
    allow_skip: bool = False
    retryable: bool = False
    requires_confirmation: bool = True

    def __post_init__(self) -> None:
        validate_host_action_policy(max_attempts=self.max_attempts)


@dataclass(slots=True)
class CreateFolderInput:
    name: str
    parent_folder_id: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class CreateDocumentInput:
    title: str
    body: str
    folder_id: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class UpdateDocumentInput:
    document_type: str
    document_id: str
    title: str | None = None
    body: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class MoveDocumentInput:
    document_type: str
    document_id: str
    target_folder_id: str
    source_folder_id: str | None = None


@dataclass(slots=True)
class LinkDocumentsInput:
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    relationship: str = "related"
    metadata: Metadata = field(default_factory=dict)


HostActionInput: TypeAlias = (
    CreateFolderInput
    | CreateDocumentInput
    | UpdateDocumentInput
    | MoveDocumentInput
    | LinkDocumentsInput
)


@dataclass(slots=True)
class CreateFolderOutput:
    folder_id: str
    name: str | None = None
    parent_folder_id: str | None = None


@dataclass(slots=True)
class CreateDocumentOutput:
    created_document_id: str
    created_document_type: str = "document"
    source_version: str | None = None
    folder_id: str | None = None


@dataclass(slots=True)
class UpdateDocumentOutput:
    updated_document_type: str
    updated_document_id: str
    source_version: str | None = None


@dataclass(slots=True)
class MoveDocumentOutput:
    moved_document_type: str
    moved_document_id: str
    target_folder_id: str
    source_folder_id: str | None = None


@dataclass(slots=True)
class LinkDocumentsOutput:
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    relationship: str = "related"
    link_id: str | None = None


HostActionOutput: TypeAlias = (
    CreateFolderOutput
    | CreateDocumentOutput
    | UpdateDocumentOutput
    | MoveDocumentOutput
    | LinkDocumentsOutput
)


@dataclass(slots=True)
class HostAction:
    action_type: HostActionType
    summary: str
    input: HostActionInput
    action_id: str = field(default_factory=new_internal_id)
    job_id: str | None = None
    reason: str = ""
    status: HostActionStatus = HostActionStatus.PROPOSED
    attempts: int = 0
    policy: HostActionPolicy = field(default_factory=HostActionPolicy)
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_host_action_attempts(self.attempts)


@dataclass(slots=True)
class HostActionResult:
    action_id: str
    outcome: HostActionResultType
    action_type: HostActionType | None = None
    output: HostActionOutput | None = None
    error: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class ActionPlan:
    summary: str
    steps: list[str]
    host_actions: list[HostAction] = field(default_factory=list)
