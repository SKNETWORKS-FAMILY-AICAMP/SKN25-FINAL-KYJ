from __future__ import annotations

from dataclasses import dataclass

from ai_core.application.ports.document_vector_store import DocumentVectorStore


@dataclass(slots=True)
class DeleteDocumentIndexUseCase:
    documents: DocumentVectorStore

    def execute(self, *, tenant: str, entity_type: str, entity_id: str) -> None:
        self.documents.delete(tenant=tenant, entity_type=entity_type, entity_id=entity_id)
