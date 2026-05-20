from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.application.commands.projection import (
    DeleteDocumentProjectionCommand,
    DeleteFolderProjectionCommand,
    ProjectDocumentFolderRelationsCommand,
    ProjectDocumentCommand,
    ProjectFolderCommand,
)


class ProjectDocumentChunkVectorsInboundPort(Protocol):
    def execute(self, command: ProjectDocumentCommand) -> None:
        ...


class DeleteDocumentChunkVectorsInboundPort(Protocol):
    def execute(self, command: DeleteDocumentProjectionCommand) -> None:
        ...


class ProjectDocumentVectorInboundPort(Protocol):
    def execute(self, command: ProjectDocumentCommand) -> None:
        ...


class DeleteDocumentVectorInboundPort(Protocol):
    def execute(self, command: DeleteDocumentProjectionCommand) -> None:
        ...


class ProjectDocumentSignalVectorsInboundPort(Protocol):
    def execute(self, command: ProjectDocumentCommand) -> None:
        ...


class DeleteDocumentSignalVectorsInboundPort(Protocol):
    def execute(self, command: DeleteDocumentProjectionCommand) -> None:
        ...


class ProjectDocumentGraphInboundPort(Protocol):
    def execute(self, command: ProjectDocumentCommand) -> None:
        ...


class ProjectDocumentFolderRelationsGraphInboundPort(Protocol):
    def execute(self, command: ProjectDocumentFolderRelationsCommand) -> None:
        ...


class DeleteDocumentGraphInboundPort(Protocol):
    def execute(self, command: DeleteDocumentProjectionCommand) -> None:
        ...


class ProjectFolderVectorInboundPort(Protocol):
    def execute(self, command: ProjectFolderCommand) -> None:
        ...


class DeleteFolderVectorInboundPort(Protocol):
    def execute(self, command: DeleteFolderProjectionCommand) -> None:
        ...


class ProjectFolderSignalVectorsInboundPort(Protocol):
    def execute(self, command: ProjectFolderCommand) -> None:
        ...


class DeleteFolderSignalVectorsInboundPort(Protocol):
    def execute(self, command: DeleteFolderProjectionCommand) -> None:
        ...


class ProjectFolderGraphInboundPort(Protocol):
    def execute(self, command: ProjectFolderCommand) -> None:
        ...


class DeleteFolderGraphInboundPort(Protocol):
    def execute(self, command: DeleteFolderProjectionCommand) -> None:
        ...
