from __future__ import annotations

from dataclasses import dataclass

from ai_core.application.ports.document_keyword_store import DocumentKeywordSearchStore
from ai_core.application.ports.document_vector_store import DocumentVectorStore
from ai_core.common.validation import require_non_blank


@dataclass(slots=True)
class DeleteDocumentIndexUseCase:
    documents: DocumentVectorStore
    keywords: DocumentKeywordSearchStore | None = None

    def execute(self, *, tenant: str, entity_type: str, entity_id: str) -> None:
        require_non_blank(tenant, "tenant")
        require_non_blank(entity_type, "entity_type")
        require_non_blank(entity_id, "entity_id")
        self.documents.delete(tenant=tenant, entity_type=entity_type, entity_id=entity_id)
        if self.keywords is not None:
            self.keywords.delete(tenant=tenant, entity_type=entity_type, entity_id=entity_id)
