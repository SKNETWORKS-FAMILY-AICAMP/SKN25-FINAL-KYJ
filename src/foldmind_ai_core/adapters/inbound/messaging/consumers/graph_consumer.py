from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.adapters.inbound.messaging.message_codec import (
    delete_document_projection_command_from_outbox,
    delete_folder_projection_command_from_outbox,
    invalidate_folder_signals_command_from_outbox,
    project_document_command_from_outbox,
    project_document_folder_relations_command_from_outbox,
    project_folder_command_from_outbox,
    project_folder_signals_command_from_outbox,
)
from foldmind_ai_core.core.application.ports.inbound.projection import (
    GraphProjectionServicePort,
)
from foldmind_ai_core.core.domain.models.outbox import OutboxEvent


@dataclass(slots=True)
class DocumentGraphIndexedConsumer:
    service: GraphProjectionServicePort

    async def consume_outbox_event(self, event: OutboxEvent) -> None:
        await self.service.project_document_graph(
            project_document_command_from_outbox(event)
        )


@dataclass(slots=True)
class DocumentGraphFolderRelationsIndexedConsumer:
    service: GraphProjectionServicePort

    async def consume_outbox_event(self, event: OutboxEvent) -> None:
        await self.service.project_document_folder_relations(
            project_document_folder_relations_command_from_outbox(event)
        )


@dataclass(slots=True)
class DocumentGraphDeletedConsumer:
    service: GraphProjectionServicePort

    async def consume_outbox_event(self, event: OutboxEvent) -> None:
        await self.service.delete_document_graph(
            delete_document_projection_command_from_outbox(event)
        )


@dataclass(slots=True)
class FolderGraphIndexedConsumer:
    service: GraphProjectionServicePort

    async def consume_outbox_event(self, event: OutboxEvent) -> None:
        await self.service.project_folder_graph(project_folder_command_from_outbox(event))


@dataclass(slots=True)
class FolderSignalsGraphIndexedConsumer:
    service: GraphProjectionServicePort

    async def consume_outbox_event(self, event: OutboxEvent) -> None:
        await self.service.project_folder_signals(
            project_folder_signals_command_from_outbox(event)
        )


@dataclass(slots=True)
class FolderSignalsGraphInvalidatedConsumer:
    service: GraphProjectionServicePort

    async def consume_outbox_event(self, event: OutboxEvent) -> None:
        await self.service.invalidate_folder_signals(
            invalidate_folder_signals_command_from_outbox(event)
        )


@dataclass(slots=True)
class FolderGraphDeletedConsumer:
    service: GraphProjectionServicePort

    async def consume_outbox_event(self, event: OutboxEvent) -> None:
        await self.service.delete_folder_graph(
            delete_folder_projection_command_from_outbox(event)
        )
