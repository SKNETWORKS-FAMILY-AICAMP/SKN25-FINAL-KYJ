from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeAlias

from foldmind_ai_core.shared.types import Metadata


@dataclass(frozen=True, slots=True)
class TaskRequestContextCommand:
    requested_at: str
    document_id: str | None = None
    folder_id: str | None = None


@dataclass(frozen=True, slots=True)
class CreateFolderOutputCommand:
    folder_id: str
    name: str | None = None
    parent_folder_id: str | None = None


@dataclass(frozen=True, slots=True)
class CreateDocumentOutputCommand:
    created_document_id: str
    created_document_type: str = "document"
    source_version: str | None = None
    folder_id: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateDocumentOutputCommand:
    updated_document_type: str
    updated_document_id: str
    source_version: str | None = None


@dataclass(frozen=True, slots=True)
class MoveDocumentOutputCommand:
    moved_document_type: str
    moved_document_id: str
    target_folder_id: str
    source_folder_id: str | None = None


@dataclass(frozen=True, slots=True)
class LinkDocumentsOutputCommand:
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    relationship: str = "related"
    link_id: str | None = None


HostActionOutputCommand: TypeAlias = (
    CreateFolderOutputCommand
    | CreateDocumentOutputCommand
    | UpdateDocumentOutputCommand
    | MoveDocumentOutputCommand
    | LinkDocumentsOutputCommand
)


@dataclass(frozen=True, slots=True)
class HostActionResultCommand:
    action_id: str
    outcome: str
    action_type: str | None = None
    output: HostActionOutputCommand | None = None
    error: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class CreateTaskCommand:
    tenant: str
    request: str
    context: TaskRequestContextCommand


@dataclass(slots=True)
class AppendTaskInputCommand:
    task_id: str
    request: str
    context: TaskRequestContextCommand


@dataclass(frozen=True, slots=True)
class GetTaskQuery:
    task_id: str


@dataclass(frozen=True, slots=True)
class RemoveTaskInputCommand:
    task_input_id: str


@dataclass(frozen=True, slots=True)
class RecordActionResultCommand:
    result: HostActionResultCommand
