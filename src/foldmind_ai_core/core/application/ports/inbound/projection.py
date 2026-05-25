from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.application.models.projection_commands import (
    DeleteDocumentProjectionCommand,
    DeleteFolderProjectionCommand,
    InvalidateFolderSignalsCommand,
    ProjectDocumentCommand,
    ProjectDocumentFolderRelationsCommand,
    ProjectFolderCommand,
    ProjectFolderSignalsCommand,
)


class DocumentVectorProjectionServicePort(Protocol):
    async def project_document_chunks(self, command: ProjectDocumentCommand) -> None:
        ...

    async def delete_document_chunks(
        self,
        command: DeleteDocumentProjectionCommand,
    ) -> None:
        ...

    async def project_document_vector(self, command: ProjectDocumentCommand) -> None:
        ...

    async def delete_document_vector(
        self,
        command: DeleteDocumentProjectionCommand,
    ) -> None:
        ...

    async def project_document_signals(self, command: ProjectDocumentCommand) -> None:
        ...

    async def delete_document_signals(
        self,
        command: DeleteDocumentProjectionCommand,
    ) -> None:
        ...


class FolderVectorProjectionServicePort(Protocol):
    async def project_folder_vector(self, command: ProjectFolderCommand) -> None:
        ...

    async def delete_folder_vector(
        self,
        command: DeleteFolderProjectionCommand,
    ) -> None:
        ...

    async def project_folder_signals(
        self,
        command: ProjectFolderSignalsCommand,
    ) -> None:
        ...

    async def invalidate_folder_signals(
        self,
        command: InvalidateFolderSignalsCommand,
    ) -> None:
        ...

    async def delete_folder_signals(
        self,
        command: DeleteFolderProjectionCommand,
    ) -> None:
        ...


class GraphProjectionServicePort(Protocol):
    async def project_document_graph(self, command: ProjectDocumentCommand) -> None:
        ...

    async def project_document_folder_relations(
        self,
        command: ProjectDocumentFolderRelationsCommand,
    ) -> None:
        ...

    async def delete_document_graph(
        self,
        command: DeleteDocumentProjectionCommand,
    ) -> None:
        ...

    async def project_folder_graph(self, command: ProjectFolderCommand) -> None:
        ...

    async def project_folder_signals(
        self,
        command: ProjectFolderSignalsCommand,
    ) -> None:
        ...

    async def invalidate_folder_signals(
        self,
        command: InvalidateFolderSignalsCommand,
    ) -> None:
        ...

    async def delete_folder_graph(
        self,
        command: DeleteFolderProjectionCommand,
    ) -> None:
        ...
