from __future__ import annotations

import unittest
from types import SimpleNamespace
from typing import Any, cast

from foldmind_ai_core.core.application.commands.recommendation import RecommendFolderCommand
from foldmind_ai_core.core.application.errors import ResourceNotFoundError
from foldmind_ai_core.core.application.queries.retrieval import (
    RequestContext,
    RetrievalQuery,
    SearchScope,
)
from foldmind_ai_core.core.application.results.retrieval import (
    FolderRecommendationResultItem,
    RecommendFolderResult,
)
from foldmind_ai_core.core.application.services.folder_recommendation_source_resolver import (
    FolderRecommendationSource,
    FolderRecommendationSourceRequest,
    FolderRecommendationSourceResolver,
)
from foldmind_ai_core.core.application.workflows.state.execution import (
    WorkflowArtifactName,
)
from foldmind_ai_core.core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.core.application.workflows.steps.executor import WorkflowStepExecutor
from foldmind_ai_core.core.application.workflows.steps.recommendation import recommend_folder
from foldmind_ai_core.core.domain.models.reference.documents import SourceDocument
from foldmind_ai_core.core.domain.models.retrieval.results import (
    DocumentRetrievalResult,
    RetrievedFolder,
)
from foldmind_ai_core.core.domain.models.workflow.tasks import (
    TaskAnalysis,
    TaskContext,
    TaskSnapshot,
    TaskStatus,
)

REQUEST_RECOMMEND_CURRENT_DOCUMENT_FOLDER = (
    "내 폴더 중 이 문서와 "
    "가장 관련 있는 곳을 추천해줘"
)


class FakeIndexedDocumentSources:
    def __init__(
        self,
        source: SourceDocument | None = None,
        folder_ids: tuple[str, ...] = (),
    ) -> None:
        self.sources = {source.document_id: source} if source is not None else {}
        self.folder_ids = folder_ids
        self.calls: list[tuple[str, str]] = []
        self.folder_calls: list[tuple[str, str]] = []

    def get_current_document_source(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> SourceDocument | None:
        self.calls.append((tenant, document_id))
        return self.sources.get(document_id)

    def get_current_document_folder_ids(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> tuple[str, ...]:
        self.folder_calls.append((tenant, document_id))
        return self.folder_ids


class FakeGraphStore:
    def __init__(
        self,
        folders_by_document: dict[str, tuple[RetrievedFolder, ...]] | None = None,
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
    ) -> dict[str, tuple[RetrievedFolder, ...]]:
        self.calls.append((tenant, document_ids))
        return self.folders_by_document

    def delete_document(self, *, document_id: str) -> None:
        raise AssertionError("Graph document deletes are not expected in this test.")

    def delete_folder(self, *, folder_id: str) -> None:
        raise AssertionError("Graph folder deletes are not expected in this test.")

    def delete_folder_signals(self, *, folder_id: str) -> None:
        raise AssertionError("Folder signal deletes are not expected in this test.")

    def delete_folder_signals_before_input_revision(
        self,
        *,
        folder_id: str,
        folder_signal_input_revision: int,
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


class CapturingRecommendFolderUseCase:
    def __init__(self) -> None:
        self.command: RecommendFolderCommand | None = None

    def execute(self, command: RecommendFolderCommand) -> RecommendFolderResult:
        self.command = command
        return RecommendFolderResult(
            primary=FolderRecommendationResultItem(
                folder_id="folder-1",
                reason="Relevant indexed source.",
                score=0.8,
            )
        )


class StaticFolderRecommendationSourceResolver:
    def __init__(self, source: FolderRecommendationSource) -> None:
        self.source = source

    def resolve(
        self,
        request: FolderRecommendationSourceRequest,
    ) -> FolderRecommendationSource:
        return self.source


class FolderRecommendationSourceResolverTests(unittest.TestCase):
    def test_context_document_uses_indexed_source_and_excludes_current_folders(
        self,
    ) -> None:
        source = _source_document(
            document_id="doc-1",
            body="Indexed signal summary.",
        )
        resolver = FolderRecommendationSourceResolver(
            indexed_documents=FakeIndexedDocumentSources(source),
            graph=FakeGraphStore(
                {
                    "doc-1": (
                        _retrieved_folder("graph-folder"),
                        _retrieved_folder("graph-folder"),
                    )
                }
            ),
        )

        resolved = resolver.resolve(
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

    def test_context_document_without_current_index_fails_without_request_text_fallback(
        self,
    ) -> None:
        resolver = FolderRecommendationSourceResolver(
            indexed_documents=FakeIndexedDocumentSources(),
            graph=FakeGraphStore(),
        )

        with self.assertRaises(ResourceNotFoundError):
            resolver.resolve(
                FolderRecommendationSourceRequest(
                    tenant="tenant-1",
                    request_text="recommend a folder",
                    requested_at="2026-05-17T09:30:00+09:00",
                    context_document_id="doc-missing",
                )
            )

    def test_explicit_document_text_takes_precedence_over_indexed_source(self) -> None:
        repository = FakeIndexedDocumentSources(_source_document(document_id="doc-1"))
        resolver = FolderRecommendationSourceResolver(
            indexed_documents=repository,
            graph=FakeGraphStore(),
        )

        resolved = resolver.resolve(
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

    def test_recommend_folder_step_uses_resolved_source_for_command(self) -> None:
        recommender = CapturingRecommendFolderUseCase()
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
                folder_recommendation_sources=StaticFolderRecommendationSourceResolver(
                    source
                ),
                recommend_folder=recommender,
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

        outcome = recommend_folder(cast(Any, ctx), state, query, {})

        self.assertIsNotNone(recommender.command)
        self.assertEqual(recommender.command.body, "Indexed signal body.")
        self.assertEqual(recommender.command.folder_ids, ("folder-current",))
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


def _retrieved_folder(folder_id: str) -> RetrievedFolder:
    return RetrievedFolder(
        tenant="tenant-1",
        folder_id=folder_id,
        source_version="folder-v1",
    )


if __name__ == "__main__":
    unittest.main()
