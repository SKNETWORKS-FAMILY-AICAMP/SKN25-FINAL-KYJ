from __future__ import annotations

import unittest

from foldmind_ai_core.core.application.prompts import (
    PROMPT_ANSWER_GENERATION,
    PROMPT_DRAFT_GENERATION,
    PROMPT_IDEAS_EXPLORATION,
    PROMPT_SUMMARIZATION,
)
from foldmind_ai_core.core.application.models.search import RequestContext
from foldmind_ai_core.core.application.models.retrieval import RetrievalQuery
from foldmind_ai_core.core.application.workflows.artifacts.registry import (
    WorkflowArtifactRegistry,
)
from foldmind_ai_core.core.application.workflows.state.execution import WorkflowArtifactName
from foldmind_ai_core.core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.core.application.workflows.steps.generation import (
    answer_question,
    explore_ideas,
    generate_draft,
    summarize_documents,
    synthesized_report,
)
from foldmind_ai_core.core.application.workflows.steps.retrieval import (
    analyze_documents,
    expand_signal_evidence,
    extract_on_demand_signals,
    synthesize_signals,
)
from foldmind_ai_core.core.application.workflows.steps.retrieval_artifacts import (
    document_retrieval_or_search,
    document_search_result,
    document_summaries,
    related_retrieval,
    signal_evidence_from_results,
)
from foldmind_ai_core.core.application.models.generation import DraftResult, GeneratedTextResult
from foldmind_ai_core.core.application.models.retrieval import (
    FolderRetrievalResult,
    RetrievalResult,
    RetrievedDocument,
    RetrievedSignal,
    SignalRetrievalResult,
)
from foldmind_ai_core.core.domain.models.document_chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder
from foldmind_ai_core.core.domain.models.document_signals import DocumentSignalEvidence
from foldmind_ai_core.core.domain.models.tasks import (
    TaskAnalysis,
    TaskContext,
    TaskSnapshot,
    TaskStatus,
)
from foldmind_ai_core.shared.validation import InvalidInputError


class FakeDocumentSearch:
    def __init__(self, results: list[RetrievalResult] | None = None) -> None:
        self.calls = 0
        self.results = results or []

    async def search(
        self,
        query: RetrievalQuery,
        *,
        require_comprehensive_search: bool = False,
    ) -> tuple[RetrievalResult, ...]:
        self.calls += 1
        return tuple(self.results)


class FakeSignalSearch:
    def __init__(self, results: list[SignalRetrievalResult] | None = None) -> None:
        self.calls = 0
        self.results = results or []

    async def search(
        self,
        query: RetrievalQuery,
        *,
        signal_type: str | None = None,
        top_k: int = 20,
    ) -> tuple[SignalRetrievalResult, ...]:
        self.calls += 1
        return tuple(self.results)


class FakeContextGenerator:
    def __init__(self) -> None:
        self.calls = 0
        self.instructions: list[str] = []
        self.prompt_names: list[str] = []

    async def generate(
        self,
        *,
        prompt_name: str,
        instruction: str,
        citations: list[RetrievalResult],
    ) -> GeneratedTextResult:
        self.calls += 1
        self.prompt_names.append(prompt_name)
        self.instructions.append(instruction)
        return GeneratedTextResult(text="generated text", citations=citations)


class WorkflowArtifactLogicTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_document_retrieval_artifact_prevents_duplicate_search(
        self,
    ) -> None:
        state = _state()
        state.artifacts.write(WorkflowArtifactName.DOCUMENT_RETRIEVAL, [])
        search = FakeDocumentSearch()
        ctx = _Context(
            artifacts=WorkflowArtifactRegistry(),
            document_search=search,
        )

        results = await document_retrieval_or_search(ctx, state, _query())

        self.assertEqual(results, [])
        self.assertEqual(search.calls, 0)

    async def test_document_retrieval_fallback_converts_application_results(
        self,
    ) -> None:
        state = _state()
        search = FakeDocumentSearch(
            [RetrievalResult(chunk=_chunk("doc-1"), score=0.75)]
        )
        ctx = _Context(
            artifacts=WorkflowArtifactRegistry(),
            document_search=search,
        )

        results = await document_retrieval_or_search(ctx, state, _query())

        self.assertEqual(search.calls, 1)
        self.assertIsInstance(results[0], RetrievalResult)
        self.assertEqual(results[0].chunk.document_id, "doc-1")
        self.assertEqual(results[0].score, 0.75)

    def test_empty_document_summaries_artifact_prevents_synthetic_summary(self) -> None:
        state = _state()
        state.artifacts.write(WorkflowArtifactName.DOCUMENT_SUMMARIES, [])
        context_generator = FakeContextGenerator()
        ctx = _Context(
            artifacts=WorkflowArtifactRegistry(),
            context_generator=context_generator,
        )

        result = synthesized_report(ctx, state)

        self.assertEqual(result, GeneratedTextResult(text="", citations=[]))
        self.assertEqual(context_generator.calls, 0)

    async def test_generation_steps_pass_action_prompt_and_instruction(self) -> None:
        state = _state()
        state.artifacts.write(
            WorkflowArtifactName.DOCUMENT_RETRIEVAL,
            [RetrievalResult(chunk=_chunk("doc-1"), score=0.9)],
        )
        context_generator = FakeContextGenerator()
        ctx = _Context(
            artifacts=WorkflowArtifactRegistry(),
            context_generator=context_generator,
        )

        cases = (
            (
                answer_question,
                PROMPT_ANSWER_GENERATION,
                "질문에 답한다.",
                WorkflowArtifactName.ANSWER,
            ),
            (
                summarize_documents,
                PROMPT_SUMMARIZATION,
                "현재 문서를 세 줄로 요약한다.",
                WorkflowArtifactName.SUMMARY,
            ),
            (
                explore_ideas,
                PROMPT_IDEAS_EXPLORATION,
                "아이디어를 확장한다.",
                WorkflowArtifactName.IDEAS,
            ),
        )
        for step_function, prompt_name, instruction, artifact_name in cases:
            with self.subTest(prompt_name=prompt_name):
                outcome = await step_function(
                    ctx,
                    state,
                    _query(),
                    {"instruction": instruction},
                )

                self.assertEqual(context_generator.prompt_names[-1], prompt_name)
                self.assertEqual(context_generator.instructions[-1], instruction)
                self.assertIn(artifact_name, outcome.artifacts)

    async def test_generate_draft_wraps_context_generation_result_as_draft(self) -> None:
        state = _state()
        state.artifacts.write(
            WorkflowArtifactName.DOCUMENT_RETRIEVAL,
            [RetrievalResult(chunk=_chunk("doc-1"), score=0.9)],
        )
        context_generator = FakeContextGenerator()
        ctx = _Context(
            artifacts=WorkflowArtifactRegistry(),
            context_generator=context_generator,
        )

        outcome = await generate_draft(
            ctx,
            state,
            _query(),
            {"instruction": "보고서 초안을 작성한다."},
        )

        self.assertEqual(context_generator.prompt_names, [PROMPT_DRAFT_GENERATION])
        self.assertEqual(context_generator.instructions, ["보고서 초안을 작성한다."])
        self.assertEqual(
            outcome.artifacts[WorkflowArtifactName.DRAFT],
            DraftResult(
                draft="generated text",
                citations=[RetrievalResult(chunk=_chunk("doc-1"), score=0.9)],
            ),
        )

    async def test_document_summaries_do_not_fall_back_to_unrelated_retrieval(
        self,
    ) -> None:
        state = _state()
        state.artifacts.write(
            WorkflowArtifactName.DOCUMENT_RETRIEVAL,
            [RetrievalResult(chunk=_chunk("doc-1"), score=0.9)],
        )
        state.artifacts.write(
            WorkflowArtifactName.RELEVANT_DOCUMENTS,
            [
                RetrievedDocument(
                    tenant="tenant-1",
                    document_type="document",
                    document_id="doc-2",
                    source_version="v1",
                    created_at="2026-05-01T10:00:00+09:00",
                    updated_at="2026-05-02T11:00:00+09:00",
                )
            ],
        )
        context_generator = FakeContextGenerator()
        ctx = _Context(
            artifacts=WorkflowArtifactRegistry(),
            context_generator=context_generator,
        )

        result = await document_summaries(
            ctx,
            state,
            instruction="Summarize relevant documents.",
        )

        self.assertEqual(result, [])
        self.assertEqual(context_generator.calls, 0)

    async def test_analyze_documents_passes_action_instruction_to_context_generator(
        self,
    ) -> None:
        state = _state()
        state.artifacts.write(
            WorkflowArtifactName.DOCUMENT_RETRIEVAL,
            [RetrievalResult(chunk=_chunk("doc-1"), score=0.9)],
        )
        state.artifacts.write(
            WorkflowArtifactName.RELEVANT_DOCUMENTS,
            [
                RetrievedDocument(
                    tenant="tenant-1",
                    document_type="document",
                    document_id="doc-1",
                    source_version="v1",
                    created_at="2026-05-01T10:00:00+09:00",
                    updated_at="2026-05-02T11:00:00+09:00",
                )
            ],
        )
        context_generator = FakeContextGenerator()
        ctx = _Context(
            artifacts=WorkflowArtifactRegistry(),
            context_generator=context_generator,
        )

        outcome = await analyze_documents(
            ctx,
            state,
            _query(),
            {"instruction": "각 문서를 결정사항 관점으로 요약한다."},
        )

        self.assertEqual(context_generator.prompt_names, [PROMPT_SUMMARIZATION])
        self.assertEqual(context_generator.instructions, ["각 문서를 결정사항 관점으로 요약한다."])
        self.assertIn(WorkflowArtifactName.DOCUMENT_SUMMARIES, outcome.artifacts)

    def test_related_retrieval_orders_mixed_items_by_score(self) -> None:
        result = related_retrieval(
            documents=[RetrievalResult(chunk=_chunk("doc-1"), score=0.2)],
            folders=[
                FolderRetrievalResult(
                    folder=SourceFolder(
                        tenant="tenant-1",
                        folder_id="folder-1",
                        source_version="folder-v1",
                        name="folder-1",
                        created_at="2026-05-01T10:00:00+09:00",
                        updated_at="2026-05-02T11:00:00+09:00",
                    ),
                    score=0.9,
                )
            ],
        )

        self.assertEqual(result.items[0].score, 0.9)
        self.assertIsNotNone(result.items[0].folder)

    async def test_document_search_result_dedupes_chunks_by_document(self) -> None:
        state = _state()
        state.artifacts.write(
            WorkflowArtifactName.DOCUMENT_RETRIEVAL,
            [
                RetrievalResult(chunk=_chunk("doc-1", 0, "low evidence"), score=0.2),
                RetrievalResult(chunk=_chunk("doc-1", 1, "best evidence"), score=0.9),
                RetrievalResult(chunk=_chunk("doc-2", 0, "other evidence"), score=0.7),
            ],
        )
        ctx = _Context(artifacts=WorkflowArtifactRegistry())

        result = await document_search_result(ctx, state, _query())

        self.assertEqual([item.document.document_id for item in result.items], ["doc-1", "doc-2"])
        self.assertEqual(result.items[0].score, 0.9)
        self.assertEqual(len(result.items[0].evidence), 2)
        self.assertEqual(result.confidence, 0.9)

    async def test_document_search_result_returns_empty_output_for_empty_retrieval(
        self,
    ) -> None:
        state = _state()
        state.artifacts.write(WorkflowArtifactName.DOCUMENT_RETRIEVAL, [])
        ctx = _Context(artifacts=WorkflowArtifactRegistry())

        result = await document_search_result(ctx, state, _query())

        self.assertEqual(result.items, [])
        self.assertEqual(result.confidence, 0.0)

    async def test_expand_signal_evidence_uses_indexed_signal_evidence(self) -> None:
        state = _state()
        state.artifacts.write(
            WorkflowArtifactName.SIGNAL_RETRIEVAL,
            [_signal_result()],
        )
        ctx = _Context(artifacts=WorkflowArtifactRegistry())

        outcome = await expand_signal_evidence(ctx, state, _query(), {})

        evidence = outcome.artifacts[WorkflowArtifactName.SIGNAL_EVIDENCE]
        self.assertEqual(evidence[0].chunk.chunk_id, "chunk-1")
        self.assertEqual(evidence[0].chunk.text, "Concern quote")
        self.assertEqual(evidence[0].chunk.metadata["signal_id"], "signal-1")

    async def test_synthesize_signals_generates_from_signal_evidence(self) -> None:
        state = _state()
        state.artifacts.write(
            WorkflowArtifactName.SIGNAL_RETRIEVAL,
            [_signal_result()],
        )
        state.artifacts.write(
            WorkflowArtifactName.SIGNAL_EVIDENCE,
            [RetrievalResult(chunk=_chunk("doc-1", text="expanded quote"), score=0.9)],
        )
        context_generator = FakeContextGenerator()
        ctx = _Context(
            artifacts=WorkflowArtifactRegistry(),
            context_generator=context_generator,
        )

        outcome = await synthesize_signals(
            ctx,
            state,
            _query(),
            {"instruction": "반복 고민을 요약한다."},
        )

        self.assertEqual(context_generator.prompt_names, [PROMPT_SUMMARIZATION])
        self.assertIn("반복 고민을 요약한다.", context_generator.instructions[0])
        self.assertIn("[issue] Repeated concern", context_generator.instructions[0])
        self.assertEqual(
            outcome.artifacts[WorkflowArtifactName.SUMMARY].citations[0].chunk.text,
            "expanded quote",
        )

    async def test_extract_on_demand_signals_uses_document_evidence_when_index_is_empty(
        self,
    ) -> None:
        state = _state()
        state.artifacts.write(
            WorkflowArtifactName.DOCUMENT_RETRIEVAL,
            [RetrievalResult(chunk=_chunk("doc-1", text="raw issue evidence"), score=0.7)],
        )
        signal_search = FakeSignalSearch()
        ctx = _Context(
            artifacts=WorkflowArtifactRegistry(),
            signal_search=signal_search,
        )

        outcome = await extract_on_demand_signals(
            ctx,
            state,
            _query(),
            {"signal_type": "issue"},
        )

        signals = outcome.artifacts[WorkflowArtifactName.SIGNAL_RETRIEVAL]
        evidence = outcome.artifacts[WorkflowArtifactName.SIGNAL_EVIDENCE]
        self.assertEqual(signal_search.calls, 1)
        self.assertEqual(signals[0].signal.signal_type, "issue")
        self.assertEqual(signals[0].signal.text, "raw issue evidence")
        self.assertEqual(evidence[0].chunk.text, "raw issue evidence")

    def test_folder_signal_evidence_uses_explicit_folder_owner_id(self) -> None:
        results = signal_evidence_from_results(
            [
                SignalRetrievalResult(
                    signal=RetrievedSignal(
                        signal_id="folder-signal-1",
                        tenant="tenant-1",
                        document_type=None,
                        document_id=None,
                        owner_kind="folder",
                        folder_id="folder-1",
                        signal_type="theme",
                        signal_key="theme",
                        text="Folder theme",
                        source_version="folder-v1",
                    ),
                    score=0.8,
                )
            ]
        )

        self.assertEqual(results[0].chunk.document_id, "folder:folder-1")

    def test_signal_evidence_rejects_signal_without_owner_reference(self) -> None:
        with self.assertRaises(InvalidInputError):
            signal_evidence_from_results(
                [
                    SignalRetrievalResult(
                        signal=RetrievedSignal(
                            signal_id="signal-1",
                            tenant="tenant-1",
                            document_type=None,
                            document_id=None,
                            signal_type="theme",
                            signal_key="theme",
                            text="No owner",
                            source_version="v1",
                        ),
                        score=0.8,
                    )
                ]
            )


class _Context:
    def __init__(self, **values: object) -> None:
        self.__dict__.update(values)


def _state() -> WorkflowState:
    return WorkflowState(
        task=TaskSnapshot(
            task_id="task-1",
            tenant="tenant-1",
            request="Find documents.",
            context=TaskContext(requested_at="2026-05-17T09:30:00+09:00"),
            status=TaskStatus.CLARIFICATION_REQUIRED,
            analysis=TaskAnalysis(message="Planning."),
        )
    )


def _query() -> RetrievalQuery:
    return RetrievalQuery(
        text="Find documents.",
        request_context=RequestContext(tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"),
    )


def _chunk(
    document_id: str, chunk_index: int = 0, text: str = "retrieved evidence"
) -> DocumentChunk:
    return DocumentChunk(
        tenant="tenant-1",
        document_type="document",
        document_id=document_id,
        source_version="v1",
        document_index_input_digest="index-input-v1",
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        chunk_id=f"{document_id}:chunk:{chunk_index}",
        chunk_index=chunk_index,
        text=text,
        start_offset=0,
        end_offset=len(text),
    )


def _signal_result() -> SignalRetrievalResult:
    return SignalRetrievalResult(
        signal=RetrievedSignal(
            signal_id="signal-1",
            tenant="tenant-1",
            document_type="document",
            signal_type="issue",
            signal_key="concern",
            text="Repeated concern",
            document_id="doc-1",
            source_version="v1",
            evidence=(
                DocumentSignalEvidence(
                    chunk_id="chunk-1",
                    quote="Concern quote",
                    start_offset=0,
                    end_offset=13,
                ),
            ),
        ),
        score=0.9,
    )


if __name__ == "__main__":
    unittest.main()
