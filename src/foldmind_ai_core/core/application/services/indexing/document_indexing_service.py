from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.core.application.models.indexing import (
    DeleteDocumentIndexCommand,
    FolderSignalInvalidation,
    IndexDocumentCommand,
)
from foldmind_ai_core.core.application.mappers.outbox_events import (
    document_deleted_event,
    document_folder_relations_indexed_event,
    document_indexed_event,
    folder_signals_invalidated_event,
)
from foldmind_ai_core.core.application.ports.outbound.provider.document_signal_extractor import (
    DocumentSignalExtractor,
)
from foldmind_ai_core.core.application.ports.outbound.session.indexing_write_session import (
    IndexingWriteSession,
    IndexingWriteSessionProvider,
)
from foldmind_ai_core.core.application.models.vector_projection import VectorProjectionSpec
from foldmind_ai_core.core.application.models.indexing import IndexDocumentResult
from foldmind_ai_core.core.application.services.indexing.folder_signal_invalidation_service import (
    FolderSignalInvalidationService,
)
from foldmind_ai_core.core.domain.models.document_chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.document_index_state import DocumentIndexState
from foldmind_ai_core.core.domain.models.document_signals import (
    DocumentSignal,
)
from foldmind_ai_core.core.domain.models.document_sources import SourceDocument
from foldmind_ai_core.core.domain.models.document_folder_relations import (
    SourceDocumentFolderRelationSnapshot,
)
from foldmind_ai_core.core.domain.services.document_chunker import DocumentChunker


@dataclass(frozen=True, slots=True)
class _DeletedDocument:
    tenant: str
    document_id: str
    source_version: str
    affected_folder_ids: tuple[str, ...] = ()
    folder_signal_invalidations: tuple[FolderSignalInvalidation, ...] = ()


@dataclass(frozen=True, slots=True)
class _DocumentIndexWrite:
    applied: bool
    folder_relation_snapshot: SourceDocumentFolderRelationSnapshot | None = None
    folder_signal_invalidations: tuple[FolderSignalInvalidation, ...] = ()


@dataclass(frozen=True, slots=True)
class _FolderRelationWrite:
    affected_folder_ids: tuple[str, ...] = ()


@dataclass(slots=True)
class DocumentIndexingService:
    signal_extractor: DocumentSignalExtractor
    indexing: IndexingWriteSessionProvider
    chunker: DocumentChunker
    vector_projection_spec: VectorProjectionSpec
    folder_signal_invalidator: FolderSignalInvalidationService = field(
        default_factory=FolderSignalInvalidationService
    )

    async def index_document(self, command: IndexDocumentCommand) -> IndexDocumentResult:
        document = command.document
        relation_snapshot = _relation_snapshot_from_command(command)
        chunks = self.chunker.chunk(document)
        if not chunks:
            await self._delete_empty_document(document=document)
            return IndexDocumentResult(indexed_chunk_count=0)

        extraction = await self.signal_extractor.extract(document, chunks)
        event = document_indexed_event(
            document=document,
            chunks=tuple(chunks),
            index_record=extraction.index_record,
            signals=extraction.signals,
            vector_projection_spec=self.vector_projection_spec,
            chunking_version=self.chunker.policy.chunking.chunking_version,
        )
        async with self.indexing.transaction() as tx:
            change = await self._replace_index(
                tx=tx,
                document=document,
                relation_snapshot=relation_snapshot,
                chunks=tuple(chunks),
                index_record=extraction.index_record,
                signals=extraction.signals,
            )
            if change.applied:
                await tx.outbox.append(event)
                if change.folder_relation_snapshot is not None:
                    await tx.outbox.append(
                        document_folder_relations_indexed_event(
                            change.folder_relation_snapshot
                        )
                    )
                for invalidation in change.folder_signal_invalidations:
                    await tx.outbox.append(folder_signals_invalidated_event(invalidation))
        indexed_chunk_count = len(chunks) if change.applied else 0
        return IndexDocumentResult(indexed_chunk_count=indexed_chunk_count)

    async def _delete_empty_document(self, *, document: SourceDocument) -> None:
        async with self.indexing.transaction() as tx:
            source_is_current = await tx.document_sources.upsert_document_source(document)
            if not source_is_current:
                return
            deleted = await self._mark_deleted(tx=tx, document_id=document.document_id)
            if deleted is None:
                await tx.outbox.append(
                    document_deleted_event(
                        tenant=document.tenant,
                        document_id=document.document_id,
                        source_version=document.source_version,
                    )
                )
                return
            await self._append_deleted_events(tx=tx, deleted=deleted)

    async def delete_document(self, command: DeleteDocumentIndexCommand) -> None:
        async with self.indexing.transaction() as tx:
            deleted = await self._mark_deleted(tx=tx, document_id=command.document_id)
            if deleted is not None:
                await self._append_deleted_events(tx=tx, deleted=deleted)

    async def _replace_index(
        self,
        *,
        tx: IndexingWriteSession,
        document: SourceDocument,
        relation_snapshot: SourceDocumentFolderRelationSnapshot | None,
        chunks: tuple[DocumentChunk, ...],
        index_record: DocumentIndexState,
        signals: tuple[DocumentSignal, ...],
    ) -> _DocumentIndexWrite:
        source_is_current = await tx.document_sources.upsert_document_source(document)
        if not source_is_current:
            return _DocumentIndexWrite(applied=False)

        await tx.document_projections.replace_document_projection(
            document=document,
            chunks=chunks,
            index_record=index_record,
            signals=signals,
        )
        relation_change = await self._replace_relation_snapshot(
            tx=tx,
            snapshot=relation_snapshot,
        )
        folder_ids = (
            relation_change.affected_folder_ids
            if relation_change is not None
            else await self._affected_folder_ids_for_document(
                tx=tx,
                tenant=document.tenant,
                document_id=document.document_id,
            )
        )
        invalidations = await self.folder_signal_invalidator.invalidate(
            tx=tx,
            tenant=document.tenant,
            folder_ids=folder_ids,
        )
        return _DocumentIndexWrite(
            applied=True,
            folder_relation_snapshot=(
                relation_snapshot if relation_change is not None else None
            ),
            folder_signal_invalidations=invalidations,
        )

    async def _replace_relation_snapshot(
        self,
        *,
        tx: IndexingWriteSession,
        snapshot: SourceDocumentFolderRelationSnapshot | None,
    ) -> _FolderRelationWrite | None:
        if snapshot is None:
            return None
        previous_folder_ids = await tx.document_relations.get_folder_ids_for_document(
            tenant=snapshot.tenant,
            document_id=snapshot.document_id,
        )
        identity = await tx.document_sources.current_document_source_identity_for_update(
            tenant=snapshot.tenant,
            document_id=snapshot.document_id,
        )
        if identity is None:
            return None
        if identity.source_version != snapshot.source_version:
            return None

        await tx.document_relations.replace_folder_relations_for_document(
            snapshot=snapshot,
        )
        current_folder_ids = await tx.document_relations.get_folder_ids_for_document(
            tenant=snapshot.tenant,
            document_id=snapshot.document_id,
        )
        affected_folder_ids = await tx.folder_sources.ancestor_folder_ids(
            tenant=snapshot.tenant,
            folder_ids=tuple(sorted({*previous_folder_ids, *current_folder_ids})),
        )
        return _FolderRelationWrite(affected_folder_ids=affected_folder_ids)

    async def _affected_folder_ids_for_document(
        self,
        *,
        tx: IndexingWriteSession,
        tenant: str,
        document_id: str,
    ) -> tuple[str, ...]:
        direct_folder_ids = await tx.document_relations.get_folder_ids_for_document(
            tenant=tenant,
            document_id=document_id,
        )
        return await tx.folder_sources.ancestor_folder_ids(
            tenant=tenant,
            folder_ids=direct_folder_ids,
        )

    async def _mark_deleted(
        self,
        *,
        tx: IndexingWriteSession,
        document_id: str,
    ) -> _DeletedDocument | None:
        identity = await tx.document_sources.document_identity_for_delete(document_id)
        if identity is None:
            return None

        direct_folder_ids = await tx.document_relations.get_folder_ids_for_document(
            tenant=identity.tenant,
            document_id=identity.document_id,
        )
        signal_folder_ids = (
            await tx.folder_projections.folder_ids_with_signals_referencing_document(
                document_id=identity.document_id,
            )
        )
        affected_folder_ids = await tx.folder_sources.ancestor_folder_ids(
            tenant=identity.tenant,
            folder_ids=tuple(sorted({*direct_folder_ids, *signal_folder_ids})),
        )
        await tx.document_projections.mark_document_projection_deleted(
            tenant=identity.tenant,
            document_id=identity.document_id,
        )
        await tx.document_relations.delete_for_document(
            tenant=identity.tenant,
            document_id=identity.document_id,
        )
        await tx.document_sources.mark_document_source_deleted(
            tenant=identity.tenant,
            document_id=identity.document_id,
        )
        invalidations = await self.folder_signal_invalidator.invalidate(
            tx=tx,
            tenant=identity.tenant,
            folder_ids=affected_folder_ids,
        )
        return _DeletedDocument(
            tenant=identity.tenant,
            document_id=identity.document_id,
            source_version=identity.source_version,
            affected_folder_ids=affected_folder_ids,
            folder_signal_invalidations=invalidations,
        )

    async def _append_deleted_events(
        self,
        *,
        tx: IndexingWriteSession,
        deleted: _DeletedDocument,
    ) -> None:
        await tx.outbox.append(
            document_deleted_event(
                tenant=deleted.tenant,
                document_id=deleted.document_id,
                source_version=deleted.source_version,
                affected_folder_ids=deleted.affected_folder_ids,
            )
        )
        for invalidation in deleted.folder_signal_invalidations:
            await tx.outbox.append(folder_signals_invalidated_event(invalidation))


def _relation_snapshot_from_command(
    command: IndexDocumentCommand,
) -> SourceDocumentFolderRelationSnapshot | None:
    if command.folder_ids is None:
        return None
    document = command.document
    return SourceDocumentFolderRelationSnapshot(
        tenant=document.tenant,
        document_id=document.document_id,
        source_version=document.source_version,
        folder_ids=command.folder_ids,
    )
