from __future__ import annotations

import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any, cast

from foldmind_ai_core.core.application.errors import ResourceNotFoundError
from foldmind_ai_core.core.application.models.recommendation import (
    FolderRecommendationSource,
    FolderRecommendationSourceRequest,
)
from foldmind_ai_core.core.application.models.search import (
    RequestContext,
    SearchScope,
)
from foldmind_ai_core.core.application.models.retrieval import RetrievalQuery
from foldmind_ai_core.core.application.models.generation import (
    FolderRecommendation,
    FolderRecommendationResult,
)
from foldmind_ai_core.core.application.services.recommendation.folder_recommendation_source_resolver import (  # noqa: E501
    FolderRecommendationSourceResolver,
)
from foldmind_ai_core.core.application.workflows.state.execution import (
    WorkflowArtifactName,
)
from foldmind_ai_core.core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.core.application.workflows.steps.executor import WorkflowStepExecutor
from foldmind_ai_core.core.application.workflows.steps.recommendation import recommend_folder
from foldmind_ai_core.core.domain.models.document_sources import (
    DocumentSourceState,
    SourceDocument,
)
from foldmind_ai_core.core.application.models.retrieval import (
    DocumentRetrievalResult,
)
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder
from foldmind_ai_core.core.domain.models.tasks import (
    TaskAnalysis,
    TaskContext,
    TaskSnapshot,
    TaskStatus,
)
from foldmind_ai_core.shared.validation import InvalidInputError

REQUEST_RECOMMEND_CURRENT_DOCUMENT_FOLDER = "내 폴더 중 이 문서와 가장 관련 있는 곳을 추천해줘"


class FakeDocumentSources:
    def __init__(
        self,
        source: DocumentSourceState | None = None,
    ) -> None:
        self.sources = {source.document_id: source} if source is not None else {}
        self.calls: list[tuple[str, str]] = []

    async def get_current_document_source(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> DocumentSourceState | None:
        self.calls.append((tenant, document_id))
        return self.sources.get(document_id)


class FakeDocumentProjections:
    def __init__(
        self,
        *,
        has_current_index: bool = True,
        signal_texts: tuple[str, ...] = ("Indexed body.",),
    ) -> None:
        self.has_current_index = has_current_index
        self.signal_texts = signal_texts
        self.index_calls: list[tuple[str, str]] = []
        self.signal_calls: list[tuple[str, str]] = []

    async def has_current_document_index(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> bool:
        self.index_calls.append((tenant, document_id))
        return self.has_current_index

    async def get_document_signal_texts(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> tuple[str, ...]:
        self.signal_calls.append((tenant, document_id))
        return self.signal_texts


class FakeDocumentFolderRelations:
    def __init__(self, folder_ids: tuple[str, ...] = ()) -> None:
        self.folder_ids = folder_ids
        self.calls: list[tuple[str, str]] = []

    async def get_folder_ids_for_document(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> tuple[str, ...]:
        self.calls.append((tenant, document_id))
        return self.folder_ids


class FakeRetrievalReadSession:
    def __init__(
        self,
        *,
        document_sources: FakeDocumentSources,
        document_projections: FakeDocumentProjections,
        document_relations: FakeDocumentFolderRelations,
    ) -> None:
        self.document_sources = document_sources
        self.document_projections = document_projections
        self.document_relations = document_relations


class FakeRetrievalReadSessionProvider:
    def __init__(
        self,
        *,
        document_sources: FakeDocumentSources,
        document_projections: FakeDocumentProjections,
        document_relations: FakeDocumentFolderRelations,
    ) -> None:
        self.session_value = FakeRetrievalReadSession(
            document_sources=document_sources,
            document_projections=document_projections,
            document_relations=document_relations,
        )

    @asynccontextmanager
    async def session(self):
        yield self.session_value


class FakeGraphStore:
    def __init__(
        self,
        folders_by_document: dict[str, tuple[SourceFolder, ...]] | None = None,
    ) -> None:
        self.folders_by_document = folders_by_document or {}
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def replace_document_projection(
        self,
        *,
        relationships: object,
        signals: object,
    ) -> None:
        raise AssertionError("Graph projection writes are not expected in this test.")

    def replace_document_folder_relations(self, *, projection: object) -> None:
        raise AssertionError("Graph projection writes are not expected in this test.")

    def replace_folder_projection(self, *, relationships: object) -> None:
        raise AssertionError("Folder projection writes are not expected in this test.")

    def replace_folder_signals(self, *, signals: object) -> None:
        raise AssertionError("Folder projection writes are not expected in this test.")

    def document_ids_for_scope(self, *, tenant: str, scope: SearchScope) -> tuple[str, ...]:
        return ()

    def folders_for_documents(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
    ) -> dict[str, tuple[SourceFolder, ...]]:
        self.calls.append((tenant, document_ids))
        return self.folders_by_document

    def delete_document(self, *, tenant: str, document_id: str) -> None:
        raise AssertionError("Graph document deletes are not expected in this test.")

    def delete_folder(self, *, tenant: str, folder_id: str) -> None:
        raise AssertionError("Graph folder deletes are not expected in this test.")

    def delete_folder_signals(self, *, tenant: str, folder_id: str) -> None:
        raise AssertionError("Folder signal deletes are not expected in this test.")

    def delete_stale_folder_signals(
        self,
        *,
        tenant: str,
        folder_id: str,
        current_folder_signal_input_digest: str,
    ) -> None:
        raise AssertionError("Folder signal deletes are not expected in this test.")

    def graph_search(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[DocumentRetrievalResult]:
        return []


class CapturingFolderRecommendationService:
    def __init__(self) -> None:
        self.source: FolderRecommendationSource | None = None

    async def recommend(
        self,
        source: FolderRecommendationSource,
    ) -> FolderRecommendationResult:
        self.source = source
        return FolderRecommendationResult(
            primary=FolderRecommendation(
                folder_id="folder-1",
                reason="Relevant indexed source.",
                score=0.8,
            )
        )


class StaticFolderRecommendationSourceResolver:
    def __init__(self, source: FolderRecommendationSource) -> None:
        self.source = source

    async def resolve(
        self,
        request: FolderRecommendationSourceRequest,
    ) -> FolderRecommendationSource:
        return self.source


class FolderRecommendationSourceResolverTests(unittest.IsolatedAsyncioTestCase):
    async def test_context_document_uses_indexed_source_and_excludes_current_folders(
        self,
    ) -> None:
        resolver = FolderRecommendationSourceResolver(
            retrieval_reads=FakeRetrievalReadSessionProvider(
                document_sources=FakeDocumentSources(_source_record(document_id="doc-1")),
                document_projections=FakeDocumentProjections(
                    signal_texts=("Indexed signal summary.",),
                ),
                document_relations=FakeDocumentFolderRelations(),
            ),
            graph=FakeGraphStore(
                {
                    "doc-1": (
                        _retrieved_folder("graph-folder"),
                        _retrieved_folder("graph-folder"),
                    )
                }
            ),
        )

        resolved = await resolver.resolve(
            FolderRecommendationSourceRequest(
                tenant="tenant-1",
                request_text=REQUEST_RECOMMEND_CURRENT_DOCUMENT_FOLDER,
                requested_at="2026-05-17T09:30:00+09:00",
                context_document_id="doc-1",
                context_folder_id="context-folder",
            )
        )

        self.assertEqual(resolved.document.body, "Indexed signal summary.")
        self.assertNotEqual(
            resolved.document.body,
            REQUEST_RECOMMEND_CURRENT_DOCUMENT_FOLDER,
        )
        self.assertEqual(resolved.folder_ids, ("graph-folder", "context-folder"))

    async def test_context_document_without_current_index_fails_without_request_text_substitute(
        self,
    ) -> None:
        resolver = FolderRecommendationSourceResolver(
            retrieval_reads=FakeRetrievalReadSessionProvider(
                document_sources=FakeDocumentSources(),
                document_projections=FakeDocumentProjections(),
                document_relations=FakeDocumentFolderRelations(),
            ),
            graph=FakeGraphStore(),
        )

        with self.assertRaises(ResourceNotFoundError):
            await resolver.resolve(
                FolderRecommendationSourceRequest(
                    tenant="tenant-1",
                    request_text="recommend a folder",
                    requested_at="2026-05-17T09:30:00+09:00",
                    context_document_id="doc-missing",
                )
            )

    async def test_explicit_document_text_takes_precedence_over_indexed_source(self) -> None:
        repository = FakeDocumentSources(_source_record(document_id="doc-1"))
        resolver = FolderRecommendationSourceResolver(
            retrieval_reads=FakeRetrievalReadSessionProvider(
                document_sources=repository,
                document_projections=FakeDocumentProjections(),
                document_relations=FakeDocumentFolderRelations(),
            ),
            graph=FakeGraphStore(),
        )

        resolved = await resolver.resolve(
            FolderRecommendationSourceRequest(
                tenant="tenant-1",
                request_text="recommend a folder",
                requested_at="2026-05-17T09:30:00+09:00",
                context_document_id="doc-1",
                task_document={
                    "document_id": "doc-explicit",
                    "title": "Explicit title",
                    "body": "Explicit body",
                    "folder_ids": ["folder-explicit"],
                },
            )
        )

        self.assertEqual(repository.calls, [])
        self.assertEqual(resolved.document.document_id, "doc-explicit")
        self.assertEqual(resolved.document.title, "Explicit title")
        self.assertEqual(resolved.document.body, "Explicit body")
        self.assertEqual(resolved.folder_ids, ("folder-explicit",))

    async def test_malformed_explicit_document_payload_is_invalid_input(self) -> None:
        resolver = FolderRecommendationSourceResolver(
            retrieval_reads=FakeRetrievalReadSessionProvider(
                document_sources=FakeDocumentSources(),
                document_projections=FakeDocumentProjections(),
                document_relations=FakeDocumentFolderRelations(),
            ),
            graph=FakeGraphStore(),
        )

        for payload in (
            ["invalid"],
            {"body": ["invalid"]},
            {"body": "Explicit body", "metadata": ["invalid"]},
            {"body": "Explicit body", "folder_ids": [None]},
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(InvalidInputError):
                    await resolver.resolve(
                        FolderRecommendationSourceRequest(
                            tenant="tenant-1",
                            request_text="recommend a folder",
                            requested_at="2026-05-17T09:30:00+09:00",
                            task_document=payload,
                        )
                    )

    async def test_request_text_source_without_context_gets_stable_internal_document_id(
        self,
    ) -> None:
        resolver = FolderRecommendationSourceResolver(
            retrieval_reads=FakeRetrievalReadSessionProvider(
                document_sources=FakeDocumentSources(),
                document_projections=FakeDocumentProjections(),
                document_relations=FakeDocumentFolderRelations(),
            ),
            graph=FakeGraphStore(),
        )
        request = FolderRecommendationSourceRequest(
            tenant="tenant-1",
            request_text="recommend a folder",
            requested_at="2026-05-17T09:30:00+09:00",
        )

        first = await resolver.resolve(request)
        second = await resolver.resolve(request)

        self.assertTrue(first.document.document_id.startswith("task-document-"))
        self.assertEqual(first.document.document_id, second.document.document_id)
        self.assertEqual(first.document.body, "recommend a folder")
        self.assertEqual(resolver.graph.calls, [])

    async def test_recommend_folder_step_uses_resolved_source_for_command(self) -> None:
        recommender = CapturingFolderRecommendationService()
        source = FolderRecommendationSource(
            document=_source_document(
                document_id="doc-1",
                body="Indexed signal body.",
            ),
            folder_ids=("folder-current",),
        )
        ctx = cast(
            WorkflowStepExecutor,
            SimpleNamespace(
                folder_recommendation_sources=StaticFolderRecommendationSourceResolver(source),
                folder_recommendation=recommender,
            ),
        )
        state = WorkflowState(
            task=TaskSnapshot(
                task_id="task-1",
                tenant="tenant-1",
                request="recommend a folder",
                context=TaskContext(
                    requested_at="2026-05-17T09:30:00+09:00",
                    document_id="doc-1",
                ),
                status=TaskStatus.CLARIFICATION_REQUIRED,
                analysis=TaskAnalysis(message="Planning."),
            )
        )
        query = RetrievalQuery(
            text="recommend a folder",
            request_context=RequestContext(
                tenant="tenant-1",
                requested_at="2026-05-17T09:30:00+09:00",
                document_id="doc-1",
            ),
        )

        outcome = await recommend_folder(cast(Any, ctx), state, query, {})

        self.assertIsNotNone(recommender.source)
        self.assertEqual(recommender.source.document.body, "Indexed signal body.")
        self.assertEqual(recommender.source.folder_ids, ("folder-current",))
        self.assertIn(WorkflowArtifactName.FOLDER_RECOMMENDATION, outcome.artifacts)
        self.assertEqual(outcome.output.primary.folder_id, "folder-1")


def _source_document(
    *,
    document_id: str,
    body: str = "Indexed body.",
) -> SourceDocument:
    return SourceDocument(
        tenant="tenant-1",
        document_type="document",
        document_id=document_id,
        source_version="v1",
        title="Indexed title",
        body=body,
        created_at="2026-05-17T09:30:00+09:00",
        updated_at="2026-05-17T09:30:00+09:00",
    )


def _source_record(*, document_id: str) -> DocumentSourceState:
    return DocumentSourceState(
        tenant="tenant-1",
        document_type="document",
        document_id=document_id,
        source_version="v1",
        title="Indexed title",
        created_at="2026-05-17T09:30:00+09:00",
        updated_at="2026-05-17T09:30:00+09:00",
        content_digest=f"content-digest-{document_id}",
        content_size_bytes=len(document_id.encode("utf-8")),
    )


def _retrieved_folder(folder_id: str) -> SourceFolder:
    return SourceFolder(
        tenant="tenant-1",
        folder_id=folder_id,
        source_version="folder-v1",
        name=folder_id,
        created_at="2026-05-17T09:30:00+09:00",
        updated_at="2026-05-17T09:30:00+09:00",
    )


if __name__ == "__main__":
    unittest.main()
