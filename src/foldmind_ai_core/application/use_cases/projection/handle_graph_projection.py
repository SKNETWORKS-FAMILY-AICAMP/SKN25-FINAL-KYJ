from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.ports.outbound.graph_repository import GraphRepository
from foldmind_ai_core.domain.indexing.projection_events import (
    DocumentDeletedProjectionEvent,
    DocumentIndexedProjectionEvent,
    FolderDeletedProjectionEvent,
    FolderIndexedProjectionEvent,
)
from foldmind_ai_core.domain.knowledge_graph.models import (
    DocumentConceptProjection,
    DocumentRelationshipProjection,
    FolderRelationshipProjection,
)


@dataclass(slots=True)
class HandleDocumentGraphIndexedProjectionUseCase:
    graph: GraphRepository

    def handle(self, event: DocumentIndexedProjectionEvent) -> None:
        self.graph.replace_document_projection(
            relationships=DocumentRelationshipProjection.from_source_document(
                event.document
            ),
            concepts=DocumentConceptProjection.from_profile(event.profile),
        )


@dataclass(slots=True)
class HandleDocumentGraphDeletedProjectionUseCase:
    graph: GraphRepository

    def handle(self, event: DocumentDeletedProjectionEvent) -> None:
        self.graph.delete_document(document_id=event.document_id)


@dataclass(slots=True)
class HandleFolderGraphIndexedProjectionUseCase:
    graph: GraphRepository

    def handle(self, event: FolderIndexedProjectionEvent) -> None:
        self.graph.replace_folder_hierarchy(
            FolderRelationshipProjection.from_source_folder(event.folder)
        )


@dataclass(slots=True)
class HandleFolderGraphDeletedProjectionUseCase:
    graph: GraphRepository

    def handle(self, event: FolderDeletedProjectionEvent) -> None:
        self.graph.delete_folder(folder_id=event.folder_id)
