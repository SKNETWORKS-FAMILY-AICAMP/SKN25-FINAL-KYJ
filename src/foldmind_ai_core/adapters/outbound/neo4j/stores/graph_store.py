from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from foldmind_ai_core.adapters.outbound.neo4j.projection import (
    delete_document_projection,
    delete_folder_projection,
    delete_folder_signal_projection,
    delete_stale_folder_signal_projection,
)
from foldmind_ai_core.adapters.outbound.neo4j.projection import (
    replace_document_folder_relations as run_replace_document_folder_relations,
)
from foldmind_ai_core.adapters.outbound.neo4j.projection import (
    replace_document_projection as run_replace_document_projection,
)
from foldmind_ai_core.adapters.outbound.neo4j.projection import (
    replace_folder_projection as run_replace_folder_projection,
)
from foldmind_ai_core.adapters.outbound.neo4j.projection import (
    replace_folder_signal_projection as run_replace_folder_signal_projection,
)
from foldmind_ai_core.adapters.outbound.neo4j.search import (
    document_ids_for_scope as run_document_ids_for_scope,
)
from foldmind_ai_core.adapters.outbound.neo4j.search import (
    folders_for_documents as run_folders_for_documents,
)
from foldmind_ai_core.adapters.outbound.neo4j.search import (
    graph_search as run_graph_search,
)
from foldmind_ai_core.core.application.errors import ProviderCallError
from foldmind_ai_core.core.domain.models.document_folder_relations import (
    SourceDocumentFolderRelationSnapshot,
)
from foldmind_ai_core.core.domain.models.document_index_state import DocumentIndexState
from foldmind_ai_core.core.domain.models.document_signals import DocumentSignal
from foldmind_ai_core.core.domain.models.document_sources import DocumentSourceState
from foldmind_ai_core.core.domain.models.folder_signals import FolderSignal
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder
from foldmind_ai_core.core.application.models.search import SearchScope
from foldmind_ai_core.core.application.models.retrieval import DocumentRetrievalResult

ResultT = TypeVar("ResultT")


@dataclass(slots=True)
class Neo4jGraphStore:
    client: Any

    def replace_document_projection(
        self,
        *,
        document: DocumentSourceState,
        document_index: DocumentIndexState,
        signals: tuple[DocumentSignal, ...],
    ) -> None:
        _run_with_session(
            self.client,
            lambda session: _execute_write(
                session,
                lambda tx: run_replace_document_projection(
                    tx,
                    document=document,
                    document_index=document_index,
                    signals=signals,
                ),
            ),
        )

    def replace_document_folder_relations(
        self,
        *,
        projection: SourceDocumentFolderRelationSnapshot,
    ) -> None:
        _run_with_session(
            self.client,
            lambda session: _execute_write(
                session,
                lambda tx: run_replace_document_folder_relations(
                    tx,
                    projection=projection,
                ),
            ),
        )

    def replace_folder_projection(
        self,
        *,
        folder: SourceFolder,
    ) -> None:
        _run_with_session(
            self.client,
            lambda session: _execute_write(
                session,
                lambda tx: run_replace_folder_projection(
                    tx,
                    folder=folder,
                ),
            ),
        )

    def replace_folder_signals(
        self,
        *,
        folder: SourceFolder,
        folder_signal_input_digest: str,
        signal_generation_version: str,
        signals: tuple[FolderSignal, ...],
    ) -> None:
        _run_with_session(
            self.client,
            lambda session: _execute_write(
                session,
                lambda tx: run_replace_folder_signal_projection(
                    tx,
                    folder=folder,
                    folder_signal_input_digest=folder_signal_input_digest,
                    signal_generation_version=signal_generation_version,
                    signals=signals,
                ),
            ),
        )

    def document_ids_for_scope(
        self,
        *,
        tenant: str,
        scope: SearchScope,
    ) -> tuple[str, ...]:
        return _run_with_session(
            self.client,
            lambda session: run_document_ids_for_scope(session, tenant=tenant, scope=scope),
        )

    def folders_for_documents(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
    ) -> dict[str, tuple[SourceFolder, ...]]:
        return _run_with_session(
            self.client,
            lambda session: run_folders_for_documents(
                session,
                tenant=tenant,
                document_ids=document_ids,
            ),
        )

    def delete_document(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        _run_with_session(
            self.client,
            lambda session: _execute_write(
                session,
                lambda tx: delete_document_projection(
                    tx,
                    tenant=tenant,
                    document_id=document_id,
                ),
            ),
        )

    def delete_folder_signals(self, *, tenant: str, folder_id: str) -> None:
        _run_with_session(
            self.client,
            lambda session: _execute_write(
                session,
                lambda tx: delete_folder_signal_projection(
                    tx,
                    tenant=tenant,
                    folder_id=folder_id,
                ),
            ),
        )

    def delete_stale_folder_signals(
        self,
        *,
        tenant: str,
        folder_id: str,
        current_folder_signal_input_digest: str,
    ) -> None:
        _run_with_session(
            self.client,
            lambda session: _execute_write(
                session,
                lambda tx: delete_stale_folder_signal_projection(
                    tx,
                    tenant=tenant,
                    folder_id=folder_id,
                    current_folder_signal_input_digest=current_folder_signal_input_digest,
                ),
            ),
        )

    def delete_folder(self, *, tenant: str, folder_id: str) -> None:
        _run_with_session(
            self.client,
            lambda session: _execute_write(
                session,
                lambda tx: delete_folder_projection(
                    tx,
                    tenant=tenant,
                    folder_id=folder_id,
                ),
            ),
        )

    def graph_search(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[DocumentRetrievalResult]:
        return _run_with_session(
            self.client,
            lambda session: run_graph_search(
                session,
                tenant=tenant,
                query_text=query_text,
                top_k=top_k,
                scope=scope,
            ),
        )


def _execute_write(session: Any, operation: Callable[[Any], None]) -> None:
    if hasattr(session, "execute_write"):
        session.execute_write(operation)
        return
    operation(session)


def _run_with_session(client: Any, operation: Callable[[Any], ResultT]) -> ResultT:
    try:
        with client.session() as session:
            return operation(session)
    except ProviderCallError:
        raise
    except Exception as exc:
        raise ProviderCallError("Neo4j graph store operation failed.") from exc
