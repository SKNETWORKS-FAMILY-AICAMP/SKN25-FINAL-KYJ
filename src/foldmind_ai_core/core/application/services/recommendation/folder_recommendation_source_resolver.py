from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.errors import ResourceNotFoundError
from foldmind_ai_core.core.application.execution.blocking_io import run_blocking
from foldmind_ai_core.core.application.mappers import recommendation_sources
from foldmind_ai_core.core.application.models.recommendation import (
    FolderRecommendationSource,
    FolderRecommendationSourceRequest,
)
from foldmind_ai_core.core.application.ports.outbound.session.retrieval_read_session import (
    RetrievalReadSessionProvider,
)
from foldmind_ai_core.core.application.ports.outbound.store.graph_store import GraphStore
from foldmind_ai_core.core.domain.models.document_sources import SourceDocument


@dataclass(slots=True)
class FolderRecommendationSourceResolver:
    retrieval_reads: RetrievalReadSessionProvider
    graph: GraphStore

    async def resolve(
        self,
        request: FolderRecommendationSourceRequest,
    ) -> FolderRecommendationSource:
        document_data = recommendation_sources.document_data_from_request(request)
        if recommendation_sources.has_explicit_document_text(
            document_data,
            request.options,
        ):
            return await self._with_current_folder_exclusions(
                recommendation_sources.source_document_from_explicit_request(
                    request,
                    document_data,
                ),
                request,
                explicit_folder_ids=recommendation_sources.folder_ids_from_explicit_request(
                    request,
                    document_data,
                ),
            )
        if request.context_document_id is not None:
            source = await self._current_document_context_source(
                tenant=request.tenant,
                document_id=request.context_document_id,
            )
            if source is None:
                raise ResourceNotFoundError(
                    f"Current indexed document source not found: {request.context_document_id}"
                )
            return await self._with_current_folder_exclusions(source, request)
        return await self._with_current_folder_exclusions(
            recommendation_sources.source_document_from_explicit_request(
                request,
                document_data,
            ),
            request,
            explicit_folder_ids=recommendation_sources.folder_ids_from_explicit_request(
                request,
                document_data,
            ),
        )

    async def _with_current_folder_exclusions(
        self,
        source: SourceDocument,
        request: FolderRecommendationSourceRequest,
        explicit_folder_ids: tuple[str, ...] = (),
    ) -> FolderRecommendationSource:
        graph_folder_ids: tuple[str, ...] = ()
        if (
            source.document_id
            and not recommendation_sources.is_internal_request_document_id(
                source.document_id
            )
        ):
            folders_by_document = await run_blocking(
                self.graph.folders_for_documents,
                tenant=source.tenant,
                document_ids=(source.document_id,),
            )
            graph_folder_ids = tuple(
                folder.folder_id
                for folder in folders_by_document.get(source.document_id, ())
                if folder.folder_id.strip()
            )

        base_folder_ids = graph_folder_ids
        if not base_folder_ids and request.context_document_id is not None:
            async with self.retrieval_reads.session() as read:
                base_folder_ids = (
                    await read.document_relations.get_folder_ids_for_document(
                        tenant=request.tenant,
                        document_id=request.context_document_id,
                    )
                )
        if not base_folder_ids:
            base_folder_ids = explicit_folder_ids
        folder_ids = recommendation_sources.unique_folder_ids(
            (
                *base_folder_ids,
                *(
                    (request.context_folder_id,)
                    if request.context_folder_id is not None
                    else ()
                ),
            )
        )
        return FolderRecommendationSource(
            document=source,
            folder_ids=folder_ids,
        )

    async def _current_document_context_source(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> SourceDocument | None:
        async with self.retrieval_reads.session() as read:
            source = await read.document_sources.get_current_document_source(
                tenant=tenant,
                document_id=document_id,
            )
            if source is None:
                return None

            has_current_index = (
                await read.document_projections.has_current_document_index(
                    tenant=tenant,
                    document_id=document_id,
                )
            )
            if not has_current_index:
                return None

            signal_texts = await read.document_projections.get_document_signal_texts(
                tenant=tenant,
                document_id=document_id,
            )
        return recommendation_sources.source_document_from_indexed_projection(
            source=source,
            body="\n\n".join(signal_texts),
        )
