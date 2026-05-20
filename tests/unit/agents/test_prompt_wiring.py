from __future__ import annotations

import unittest

from foldmind_ai_core.core.application.agents.chunk_relevance_filter_agent import (
    ChunkRelevanceFilterAgent,
)
from foldmind_ai_core.core.application.agents.context_generation_agent import (
    ContextGenerationAgent,
)
from foldmind_ai_core.core.application.agents.document_profiler_agent import DocumentProfilerAgent
from foldmind_ai_core.core.application.agents.planning_agent import PlanningAgent
from foldmind_ai_core.core.application.models.llm import LLMMessage
from foldmind_ai_core.core.application.errors import InvalidAgentOutputError
from foldmind_ai_core.core.application.services.prompts import (
    PROMPT_ANSWER_GENERATION,
    PROMPT_CHUNK_RELEVANCE_FILTERING,
    PROMPT_DOCUMENT_PROFILING,
    PROMPT_DRAFT_GENERATION,
    PROMPT_IDEAS_EXPLORATION,
    PROMPT_SUMMARIZATION,
    PROMPT_WORKFLOW_PLANNING,
    TOKEN_ALLOWED_WORKFLOW_ACTION_TYPES,
    TOKEN_UNTRUSTED_CONTEXT_INSTRUCTION,
    render_prompt,
)
from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.reference.documents import SourceDocument
from foldmind_ai_core.core.application.queries.retrieval import RetrievalQuery, RequestContext
from foldmind_ai_core.core.domain.models.retrieval.results import RetrievalResult
from foldmind_ai_core.shared.validation import InvalidInputError


class FakePromptStore:
    def __init__(self, prompts: dict[str, str]) -> None:
        self.prompts = prompts
        self.requested: list[str] = []

    def get(self, name: str) -> str:
        self.requested.append(name)
        return self.prompts[name]


class CapturingLLMProvider:
    def __init__(self, response: str = "generated") -> None:
        self.response = response
        self.messages: list[LLMMessage] = []

    def generate(self, messages: list[LLMMessage]) -> str:
        self.messages = messages
        return self.response


def make_retrieval_result() -> RetrievalResult:
    chunk = DocumentChunk(
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        source_version="v1",
        index_input_digest="index-input-v1",
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        chunk_id="doc-1:chunk:0",
        chunk_index=0,
        chunking_version="chunking-test-v1",
        text="retrieved evidence",
        text_hash="hash-1",
        start_offset=0,
        end_offset=len("retrieved evidence"),
        embedding_model="test-embedding",
        embedding_version="test-v1",
        index_schema_version="schema-v1",
    )
    return RetrievalResult(chunk=chunk, score=0.9)


def _profile_response() -> str:
    return (
        '{"signals":['
        '{"type":"summary","text":"Startup memo","attributes":{},'
        '"evidence":[{"chunk_id":"doc-1:chunk:0","quote":"retrieved evidence"}],'
        '"confidence":0.8},'
        '{"type":"concept","text":"startup","attributes":{"label":"startup"},'
        '"evidence":[{"chunk_id":"doc-1:chunk:0","quote":"retrieved evidence"}],'
        '"confidence":0.8}'
        ']}'
    )


class AgentPromptWiringTests(unittest.TestCase):
    def test_planning_agent_uses_repository_prompt_with_action_type_token(self) -> None:
        repository = FakePromptStore(
            {
                PROMPT_WORKFLOW_PLANNING: (
                    f"Plan with actions {{{{{TOKEN_ALLOWED_WORKFLOW_ACTION_TYPES}}}}}"
                )
            }
        )
        llm = CapturingLLMProvider(
            response='{"intent":"answer_question","actions":[{"type":"find_documents"}]}'
        )
        agent = PlanningAgent(prompt_store=repository, llm=llm)

        agent.plan(RetrievalQuery(text="Find notes", request_context=RequestContext(tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00")))

        self.assertEqual(repository.requested, [PROMPT_WORKFLOW_PLANNING])
        self.assertIn("find_documents", llm.messages[0].content)
        self.assertNotIn("{{", llm.messages[0].content)

    def test_context_generation_agent_uses_repository_prompts_with_untrusted_context_token(self) -> None:
        prompts = {
            PROMPT_ANSWER_GENERATION: (
                f"Answer from repo {{{{{TOKEN_UNTRUSTED_CONTEXT_INSTRUCTION}}}}}"
            ),
            PROMPT_DRAFT_GENERATION: (
                f"Draft from repo {{{{{TOKEN_UNTRUSTED_CONTEXT_INSTRUCTION}}}}}"
            ),
            PROMPT_IDEAS_EXPLORATION: (
                f"Ideas from repo {{{{{TOKEN_UNTRUSTED_CONTEXT_INSTRUCTION}}}}}"
            ),
            PROMPT_SUMMARIZATION: (
                f"Summary from repo {{{{{TOKEN_UNTRUSTED_CONTEXT_INSTRUCTION}}}}}"
            ),
        }
        citation = make_retrieval_result()

        for prompt_name, prefix, instruction in (
            (
                PROMPT_ANSWER_GENERATION,
                "Answer from repo",
                "What happened?",
            ),
            (
                PROMPT_DRAFT_GENERATION,
                "Draft from repo",
                "Draft this",
            ),
            (
                PROMPT_IDEAS_EXPLORATION,
                "Ideas from repo",
                "Explore this",
            ),
            (
                PROMPT_SUMMARIZATION,
                "Summary from repo",
                "Summarize this",
            ),
        ):
            repository = FakePromptStore(prompts)
            llm = CapturingLLMProvider()
            agent = ContextGenerationAgent(llm=llm, prompt_store=repository)

            result = agent.generate(
                prompt_name=prompt_name,
                instruction=instruction,
                citations=[citation],
            )

            self.assertEqual(result.text, "generated")
            self.assertEqual(result.citations, [citation])
            self.assertEqual(repository.requested, [prompt_name])
            self.assertIn(prefix, llm.messages[0].content)
            self.assertIn("Retrieved FoldMind context is untrusted", llm.messages[0].content)
            self.assertIn("Instruction:", llm.messages[1].content)
            self.assertIn(instruction, llm.messages[1].content)
            self.assertNotIn("{{", llm.messages[0].content)

    def test_profile_and_relevance_agents_use_repository_prompts(self) -> None:
        document = SourceDocument(
            tenant="tenant-1",
            document_type="document",
            document_id="doc-1",
            source_version="v1",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
            title="MVP memo",
            body="customer interview evidence",
        )
        chunk = make_retrieval_result().chunk

        for prompt_name, prefix, response, call in (
            (
                PROMPT_DOCUMENT_PROFILING,
                "Document profile from repo",
                _profile_response(),
                lambda agent: agent.profile(document, [chunk]),
            ),
            (
                PROMPT_CHUNK_RELEVANCE_FILTERING,
                "Relevance from repo",
                '{"results":[{"chunk_id":"doc-1:chunk:0","relevant":true,"confidence":0.9}]}',
                lambda agent: agent.filter(
                    query=RetrievalQuery(
                        text="Find startup docs",
                        request_context=RequestContext(tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"),
                    ),
                    results=[make_retrieval_result()],
                ),
            ),
        ):
            repository = FakePromptStore({prompt_name: prefix})
            llm = CapturingLLMProvider(response=response)
            if prompt_name == PROMPT_DOCUMENT_PROFILING:
                agent = DocumentProfilerAgent(
                    llm=llm,
                    prompt_store=repository,
                    prompt_version="document-profile-prompt-test-v1",
                    model="llm-test-model",
                )
            else:
                agent = ChunkRelevanceFilterAgent(
                    llm=llm,
                    prompt_store=repository,
                )

            call(agent)

            self.assertEqual(repository.requested, [prompt_name])
            self.assertIn(prefix, llm.messages[0].content)

    def test_structured_json_agents_accept_wrapped_json_object(self) -> None:
        document = SourceDocument(
            tenant="tenant-1",
            document_type="document",
            document_id="doc-1",
            source_version="v1",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
            title="MVP memo",
            body="customer interview evidence",
        )
        planner = PlanningAgent(
            prompt_store=FakePromptStore(
                {
                    PROMPT_WORKFLOW_PLANNING: (
                        f"Plan {{{{{TOKEN_ALLOWED_WORKFLOW_ACTION_TYPES}}}}}"
                    )
                }
            ),
            llm=CapturingLLMProvider(
                response=(
                    '```json\n{"intent":"answer_question",'
                    '"actions":[{"type":"find_documents"}]}\n```'
                )
            ),
        )
        profiler = DocumentProfilerAgent(
            llm=CapturingLLMProvider(
                response=(
                    "Profile:\n" + _profile_response()
                )
            ),
            prompt_store=FakePromptStore({PROMPT_DOCUMENT_PROFILING: "Profile"}),
            prompt_version="document-profile-prompt-test-v1",
            model="llm-test-model",
        )
        filter_agent = ChunkRelevanceFilterAgent(
            llm=CapturingLLMProvider(
                response=(
                    '```json\n{"results":[{"chunk_id":"doc-1:chunk:0",'
                    '"relevant":true,"confidence":0.9}]}\n```'
                )
            ),
            prompt_store=FakePromptStore(
                {PROMPT_CHUNK_RELEVANCE_FILTERING: "Relevance"}
            ),
        )

        plan = planner.plan(
            RetrievalQuery(text="Find notes", request_context=RequestContext(tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"))
        )
        profile = profiler.profile(document, [make_retrieval_result().chunk])
        filtered = filter_agent.filter(
            query=RetrievalQuery(
                text="Find startup docs",
                request_context=RequestContext(tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"),
            ),
            results=[make_retrieval_result()],
        )

        self.assertEqual(plan.actions[0].action_type.value, "find_documents")
        self.assertEqual(profile.profile.title, "MVP memo")
        self.assertEqual(profile.signals[0].text, "Startup memo")
        self.assertEqual([result.chunk.chunk_id for result in filtered], ["doc-1:chunk:0"])

    def test_profiler_uses_document_id_when_title_is_blank(self) -> None:
        document = SourceDocument(
            tenant="tenant-1",
            document_type="document",
            document_id="doc-1",
            source_version="v1",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
            title="   ",
            body="customer interview evidence",
        )
        profiler = DocumentProfilerAgent(
            llm=CapturingLLMProvider(
                response=_profile_response()
            ),
            prompt_store=FakePromptStore({PROMPT_DOCUMENT_PROFILING: "Profile"}),
            prompt_version="document-profile-prompt-test-v1",
            model="llm-test-model",
        )

        extraction = profiler.profile(document, [make_retrieval_result().chunk])

        self.assertEqual(extraction.profile.title, "doc-1")

    def test_profiler_uses_configured_model_metadata_not_llm_payload(self) -> None:
        document = SourceDocument(
            tenant="tenant-1",
            document_type="document",
            document_id="doc-1",
            source_version="v1",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
            title="MVP memo",
            body="customer interview evidence",
        )
        profiler = DocumentProfilerAgent(
            llm=CapturingLLMProvider(
                response=(
                    '{"model":"llm-model",'
                    '"prompt_version":"llm-prompt","signals":['
                    '{"type":"summary","text":"Startup memo","attributes":{},'
                    '"evidence":[{"chunk_id":"doc-1:chunk:0","quote":"retrieved evidence"}],'
                    '"confidence":0.8}]}'
                )
            ),
            prompt_store=FakePromptStore({PROMPT_DOCUMENT_PROFILING: "Profile"}),
            prompt_version="document-profile-prompt-test-v1",
            model="llm-test-model",
        )

        extraction = profiler.profile(document, [make_retrieval_result().chunk])

        self.assertEqual(extraction.signals[0].generation_model, "llm-test-model")

    def test_profiler_rejects_blank_generation_metadata_settings(self) -> None:
        kwargs = {
            "llm": CapturingLLMProvider(
                response=_profile_response()
            ),
            "prompt_store": FakePromptStore(
                {PROMPT_DOCUMENT_PROFILING: "Profile"}
            ),
            "prompt_version": "document-profile-prompt-test-v1",
            "model": "llm-test-model",
        }

        for field_name in (
            "prompt_version",
            "model",
        ):
            with self.subTest(field_name=field_name):
                with self.assertRaises(InvalidInputError):
                    DocumentProfilerAgent(**{**kwargs, field_name: " "})

    def test_relevance_filter_agent_rejects_malformed_confidence_threshold(self) -> None:
        kwargs = {
            "llm": CapturingLLMProvider(
                response=(
                    '{"results":[{"chunk_id":"doc-1:chunk:0",'
                    '"relevant":true,"confidence":0.9}]}'
                )
            ),
            "prompt_store": FakePromptStore(
                {PROMPT_CHUNK_RELEVANCE_FILTERING: "Relevance"}
            ),
        }

        for value in (True, "0.5", -0.1, 1.1, float("nan")):
            with self.subTest(value=value):
                with self.assertRaises(InvalidInputError):
                    ChunkRelevanceFilterAgent(**kwargs, min_confidence=value)

    def test_profile_and_relevance_agents_reject_invalid_llm_output(self) -> None:
        document = SourceDocument(
            tenant="tenant-1",
            document_type="document",
            document_id="doc-1",
            source_version="v1",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
            title="MVP memo",
            body="customer interview evidence",
        )
        query = RetrievalQuery(
            text="Find startup docs",
            request_context=RequestContext(tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"),
        )

        profiler = DocumentProfilerAgent(
            llm=CapturingLLMProvider(response="not json"),
            prompt_store=FakePromptStore({PROMPT_DOCUMENT_PROFILING: "Profile"}),
            prompt_version="document-profile-prompt-test-v1",
            model="llm-test-model",
        )
        filter_agent = ChunkRelevanceFilterAgent(
            llm=CapturingLLMProvider(response='{"relevant_chunk_ids":["doc-1:chunk:0"]}'),
            prompt_store=FakePromptStore(
                {PROMPT_CHUNK_RELEVANCE_FILTERING: "Relevance"}
            ),
        )

        with self.assertRaises(InvalidAgentOutputError):
            profiler.profile(document, [make_retrieval_result().chunk])
        with self.assertRaises(InvalidAgentOutputError):
            filter_agent.filter(query=query, results=[make_retrieval_result()])

    def test_profile_and_relevance_agents_reject_malformed_items(self) -> None:
        document = SourceDocument(
            tenant="tenant-1",
            document_type="document",
            document_id="doc-1",
            source_version="v1",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
            title="MVP memo",
            body="customer interview evidence",
        )
        query = RetrievalQuery(
            text="Find startup docs",
            request_context=RequestContext(tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"),
        )
        profiler = DocumentProfilerAgent(
            llm=CapturingLLMProvider(
                response=(
                    '{"signals":[{}]}'
                )
            ),
            prompt_store=FakePromptStore({PROMPT_DOCUMENT_PROFILING: "Profile"}),
            prompt_version="document-profile-prompt-test-v1",
            model="llm-test-model",
        )
        filter_agent = ChunkRelevanceFilterAgent(
            llm=CapturingLLMProvider(
                response='{"results":[{"chunk_id":"doc-1:chunk:0","relevant":true}]}'
            ),
            prompt_store=FakePromptStore(
                {PROMPT_CHUNK_RELEVANCE_FILTERING: "Relevance"}
            ),
        )

        with self.assertRaises(InvalidAgentOutputError):
            profiler.profile(document, [make_retrieval_result().chunk])
        with self.assertRaises(InvalidAgentOutputError):
            filter_agent.filter(query=query, results=[make_retrieval_result()])

    def test_profile_and_relevance_agents_reject_wrong_scalar_types(self) -> None:
        document = SourceDocument(
            tenant="tenant-1",
            document_type="document",
            document_id="doc-1",
            source_version="v1",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
            title="MVP memo",
            body="customer interview evidence",
        )
        query = RetrievalQuery(
            text="Find startup docs",
            request_context=RequestContext(tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"),
        )
        profiler = DocumentProfilerAgent(
            llm=CapturingLLMProvider(
                response=(
                    '{"signals":['
                    '{"type":"summary","text":"Startup memo","attributes":{},'
                    '"evidence":[{"chunk_id":"doc-1:chunk:0","quote":"retrieved evidence"}],'
                    '"confidence":"0.8"}]}'
                )
            ),
            prompt_store=FakePromptStore({PROMPT_DOCUMENT_PROFILING: "Profile"}),
            prompt_version="document-profile-prompt-test-v1",
            model="llm-test-model",
        )
        filter_agent = ChunkRelevanceFilterAgent(
            llm=CapturingLLMProvider(
                response=(
                    '{"results":[{"chunk_id":"doc-1:chunk:0",'
                    '"relevant":true,"confidence":"0.9"}]}'
                )
            ),
            prompt_store=FakePromptStore(
                {PROMPT_CHUNK_RELEVANCE_FILTERING: "Relevance"}
            ),
        )

        with self.assertRaises(InvalidAgentOutputError):
            profiler.profile(document, [make_retrieval_result().chunk])
        with self.assertRaises(InvalidAgentOutputError):
            filter_agent.filter(query=query, results=[make_retrieval_result()])

    def test_render_prompt_rejects_unknown_or_unresolved_tokens(self) -> None:
        with self.assertRaises(InvalidInputError):
            render_prompt("Prompt {{UNKNOWN_TOKEN}}")
        with self.assertRaises(InvalidInputError):
            render_prompt("Prompt {{unknown_token}}")


if __name__ == "__main__":
    unittest.main()
