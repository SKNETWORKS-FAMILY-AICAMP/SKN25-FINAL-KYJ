from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from ai_core.api.settings import APISettings
from ai_core.application.models.llm import LLMMessage
from ai_core.application.models.queries import SearchScope
from ai_core.application.models.retrieval import FolderRetrievalResult, RetrievalResult
from ai_core.application.models.tasks import TaskEvent, TaskRequest, TaskSnapshot
from ai_core.bootstrap import AICoreDependencies, build_app, build_use_cases
from ai_core.common import Vector
from ai_core.domain.chunks import DocumentChunk
from ai_core.domain.folders import IndexedFolder


def make_chunk(chunk_id: str, text: str) -> DocumentChunk:
    return DocumentChunk(
        tenant="tenant-1",
        entity_type="document",
        entity_id="doc-1",
        version="v1",
        chunk_id=chunk_id,
        text=text,
        chunk_index=0,
        start_offset=0,
        end_offset=len(text),
    )


class FakeEmbeddingProvider:
    def embed_texts(self, texts: list[str]) -> list[Vector]:
        return [[float(len(text))] for text in texts]


class FakeDocumentVectorStore:
    def __init__(self) -> None:
        self.upserted: list[DocumentChunk] = []
        self.deleted: list[tuple[str, str, str]] = []

    def upsert(self, chunks: list[DocumentChunk], vectors: list[Vector]) -> None:
        self.upserted.extend(chunks)

    def delete(self, *, tenant: str, entity_type: str, entity_id: str) -> None:
        self.deleted.append((tenant, entity_type, entity_id))

    def similarity_search(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[RetrievalResult]:
        return [RetrievalResult(chunk=make_chunk("doc-1:chunk:dense", "dense result"), score=0.9)]


class FakeDocumentKeywordSearchStore:
    def __init__(self) -> None:
        self.upserted: list[DocumentChunk] = []
        self.deleted: list[tuple[str, str, str]] = []

    def upsert(self, chunks: list[DocumentChunk]) -> None:
        self.upserted.extend(chunks)

    def delete(self, *, tenant: str, entity_type: str, entity_id: str) -> None:
        self.deleted.append((tenant, entity_type, entity_id))

    def keyword_search(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[RetrievalResult]:
        return [
            RetrievalResult(chunk=make_chunk("doc-1:chunk:keyword", "keyword result"), score=3.0)
        ]


class FakeFolderVectorStore:
    def upsert(self, folders: list[IndexedFolder], vectors: list[Vector]) -> None:
        pass

    def delete(self, *, tenant: str, folder_id: str) -> None:
        pass

    def similarity_search(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
    ) -> list[FolderRetrievalResult]:
        return [
            FolderRetrievalResult(
                folder=IndexedFolder(tenant=tenant, folder_id="folder-1", name="Meetings"),
                score=0.8,
            )
        ]


class FakeLLM:
    def __init__(self) -> None:
        self.messages: list[LLMMessage] = []

    def generate(self, messages: list[LLMMessage]) -> str:
        self.messages = messages
        return "generated answer"


class FakeTaskStore:
    def __init__(self) -> None:
        self.items: dict[tuple[str, str], TaskSnapshot] = {}

    def create(self, request: TaskRequest, snapshot: TaskSnapshot) -> None:
        self.items[(request.tenant, request.task_id)] = snapshot

    def get(self, *, tenant: str, task_id: str) -> TaskSnapshot | None:
        return self.items.get((tenant, task_id))

    def save(self, snapshot: TaskSnapshot) -> None:
        self.items[(snapshot.tenant, snapshot.task_id)] = snapshot

    def append_event(self, *, tenant: str, task_id: str, event: TaskEvent) -> None:
        self.items[(tenant, task_id)].events.append(event)


class BootstrapTests(unittest.TestCase):
    def test_api_settings_can_be_loaded_from_environment(self) -> None:
        keys = (
            "FOLDMIND_API_TITLE",
            "FOLDMIND_API_VERSION",
            "FOLDMIND_CORS_ORIGINS",
            "FOLDMIND_CORS_ALLOW_CREDENTIALS",
        )
        previous = {key: os.environ.get(key) for key in keys}
        try:
            os.environ["FOLDMIND_API_TITLE"] = "Custom FoldMind"
            os.environ["FOLDMIND_API_VERSION"] = "9.9.9"
            os.environ["FOLDMIND_CORS_ORIGINS"] = "http://localhost:3000, https://app.test"
            os.environ["FOLDMIND_CORS_ALLOW_CREDENTIALS"] = "false"

            settings = APISettings.from_env()

            self.assertEqual(settings.title, "Custom FoldMind")
            self.assertEqual(settings.version, "9.9.9")
            self.assertEqual(
                settings.cors_origins,
                ("http://localhost:3000", "https://app.test"),
            )
            self.assertFalse(settings.cors_allow_credentials)
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_bootstrap_wires_dependencies_into_app(self) -> None:
        document_vectors = FakeDocumentVectorStore()
        document_keywords = FakeDocumentKeywordSearchStore()
        llm = FakeLLM()
        dependencies = AICoreDependencies(
            embeddings=FakeEmbeddingProvider(),
            document_vectors=document_vectors,
            document_keywords=document_keywords,
            folder_vectors=FakeFolderVectorStore(),
            llm=llm,
            tasks=FakeTaskStore(),
        )

        use_cases = build_use_cases(dependencies)
        app = build_app(dependencies)
        client = TestClient(app)

        index_response = client.post(
            "/indexing/documents",
            json={
                "document": {
                    "tenant": "tenant-1",
                    "entity_type": "document",
                    "entity_id": "doc-1",
                    "version": "v1",
                    "title": "Meeting notes",
                    "body": "Prepare next meeting",
                }
            },
        )
        answer_response = client.post(
            "/retrieval/answer",
            json={
                "query": {
                    "text": "What happened?",
                    "request_context": {"tenant": "tenant-1"},
                }
            },
        )

        self.assertIs(use_cases.answer_question.hybrid_search, use_cases.search_documents)
        self.assertEqual(index_response.status_code, 200)
        self.assertGreater(len(document_vectors.upserted), 0)
        self.assertGreater(len(document_keywords.upserted), 0)
        self.assertEqual(answer_response.status_code, 200)
        self.assertEqual(answer_response.json()["text"], "generated answer")
        self.assertGreater(len(answer_response.json()["citations"]), 0)
        self.assertGreater(len(llm.messages), 0)


if __name__ == "__main__":
    unittest.main()
