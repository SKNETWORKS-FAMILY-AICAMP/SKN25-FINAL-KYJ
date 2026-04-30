from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, TypeAlias

from ai_core.common.validation import (
    InvalidInputError,
    require_non_blank,
    require_non_blank_items,
    require_optional_non_blank,
)


class HostActionType(StrEnum):
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


@dataclass(slots=True)
class CreateDocumentInput:
    title: str
    body: str
    folder_id: str | None = None
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_optional_non_blank(self.folder_id, "folder_id")
        require_non_blank_items(self.tags, "tags")


@dataclass(slots=True)
class UpdateDocumentInput:
    entity_type: str
    entity_id: str
    title: str | None = None
    body: str | None = None
    tags: tuple[str, ...] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_non_blank(self.entity_type, "entity_type")
        require_non_blank(self.entity_id, "entity_id")
        if self.tags is not None:
            require_non_blank_items(self.tags, "tags")


@dataclass(slots=True)
class MoveDocumentInput:
    entity_type: str
    entity_id: str
    target_folder_id: str
    source_folder_id: str | None = None

    def __post_init__(self) -> None:
        require_non_blank(self.entity_type, "entity_type")
        require_non_blank(self.entity_id, "entity_id")
        require_non_blank(self.target_folder_id, "target_folder_id")
        require_optional_non_blank(self.source_folder_id, "source_folder_id")


@dataclass(slots=True)
class LinkDocumentsInput:
    source_entity_type: str
    source_entity_id: str
    target_entity_type: str
    target_entity_id: str
    relationship: str = "related"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_non_blank(self.source_entity_type, "source_entity_type")
        require_non_blank(self.source_entity_id, "source_entity_id")
        require_non_blank(self.target_entity_type, "target_entity_type")
        require_non_blank(self.target_entity_id, "target_entity_id")
        require_non_blank(self.relationship, "relationship")


HostActionInput: TypeAlias = (
    CreateDocumentInput
    | UpdateDocumentInput
    | MoveDocumentInput
    | LinkDocumentsInput
)


@dataclass(slots=True)
class CreateDocumentOutput:
    created_entity_id: str
    created_entity_type: str = "document"
    version: str | None = None
    folder_id: str | None = None

    def __post_init__(self) -> None:
        require_non_blank(self.created_entity_id, "created_entity_id")
        require_non_blank(self.created_entity_type, "created_entity_type")
        require_optional_non_blank(self.version, "version")
        require_optional_non_blank(self.folder_id, "folder_id")


@dataclass(slots=True)
class UpdateDocumentOutput:
    updated_entity_type: str
    updated_entity_id: str
    version: str | None = None

    def __post_init__(self) -> None:
        require_non_blank(self.updated_entity_type, "updated_entity_type")
        require_non_blank(self.updated_entity_id, "updated_entity_id")
        require_optional_non_blank(self.version, "version")


@dataclass(slots=True)
class MoveDocumentOutput:
    moved_entity_type: str
    moved_entity_id: str
    target_folder_id: str
    source_folder_id: str | None = None

    def __post_init__(self) -> None:
        require_non_blank(self.moved_entity_type, "moved_entity_type")
        require_non_blank(self.moved_entity_id, "moved_entity_id")
        require_non_blank(self.target_folder_id, "target_folder_id")
        require_optional_non_blank(self.source_folder_id, "source_folder_id")


@dataclass(slots=True)
class LinkDocumentsOutput:
    source_entity_type: str
    source_entity_id: str
    target_entity_type: str
    target_entity_id: str
    relationship: str = "related"
    link_id: str | None = None

    def __post_init__(self) -> None:
        require_non_blank(self.source_entity_type, "source_entity_type")
        require_non_blank(self.source_entity_id, "source_entity_id")
        require_non_blank(self.target_entity_type, "target_entity_type")
        require_non_blank(self.target_entity_id, "target_entity_id")
        require_non_blank(self.relationship, "relationship")
        require_optional_non_blank(self.link_id, "link_id")


HostActionOutput: TypeAlias = (
    CreateDocumentOutput
    | UpdateDocumentOutput
    | MoveDocumentOutput
    | LinkDocumentsOutput
)


@dataclass(slots=True)
class HostAction:
    action_type: HostActionType | str
    summary: str
    input: HostActionInput
    action_id: str | None = None
    reason: str = ""
    status: HostActionStatus = HostActionStatus.PROPOSED
    attempts: int = 0
    depends_on: list[str] = field(default_factory=list)
    policy: HostActionPolicy = field(default_factory=HostActionPolicy)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        try:
            self.action_type = HostActionType(self.action_type)
        except ValueError as exc:
            raise InvalidInputError(f"Unsupported action_type: {self.action_type}") from exc
        require_non_blank(self.summary, "summary")
        require_optional_non_blank(self.action_id, "action_id")
        require_non_blank_items(self.depends_on, "depends_on")
        self._validate_input_matches_action_type()

    def _validate_input_matches_action_type(self) -> None:
        expected_input_types = {
            HostActionType.CREATE_DOCUMENT: CreateDocumentInput,
            HostActionType.UPDATE_DOCUMENT: UpdateDocumentInput,
            HostActionType.MOVE_DOCUMENT: MoveDocumentInput,
            HostActionType.LINK_DOCUMENTS: LinkDocumentsInput,
        }
        expected_input_type = expected_input_types[self.action_type]
        if not isinstance(self.input, expected_input_type):
            raise InvalidInputError(
                f"{self.action_type} action requires {expected_input_type.__name__}."
            )


@dataclass(slots=True)
class HostActionResult:
    action_id: str
    outcome: HostActionResultType
    action_type: str | None = None
    output: HostActionOutput | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_non_blank(self.action_id, "action_id")
        require_optional_non_blank(self.action_type, "action_type")
        require_optional_non_blank(self.error, "error")
        if self.output is not None and self.action_type is None:
            raise InvalidInputError("action_type is required when output is present.")
        if self.output is not None:
            self._validate_output_matches_action_type()

    def _validate_output_matches_action_type(self) -> None:
        expected_output_types = {
            HostActionType.CREATE_DOCUMENT: CreateDocumentOutput,
            HostActionType.UPDATE_DOCUMENT: UpdateDocumentOutput,
            HostActionType.MOVE_DOCUMENT: MoveDocumentOutput,
            HostActionType.LINK_DOCUMENTS: LinkDocumentsOutput,
        }
        try:
            action_type = HostActionType(self.action_type)
        except ValueError as exc:
            raise InvalidInputError(f"Unsupported action_type: {self.action_type}") from exc
        expected_output_type = expected_output_types[action_type]
        if not isinstance(self.output, expected_output_type):
            raise InvalidInputError(
                f"{action_type} result requires {expected_output_type.__name__}."
            )


@dataclass(slots=True)
class ActionPlan:
    summary: str
    steps: list[str]
    host_actions: list[HostAction] = field(default_factory=list)

    def __post_init__(self) -> None:
        require_non_blank(self.summary, "summary")
        require_non_blank_items(self.steps, "steps")
