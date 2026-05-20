from __future__ import annotations

import unittest
from dataclasses import dataclass

from foldmind_ai_core.adapters.outbound.openai.client import OpenAIClient
from foldmind_ai_core.adapters.outbound.openai.embeddings import OpenAIEmbeddingProvider
from foldmind_ai_core.adapters.outbound.openai.errors import AIProviderError
from foldmind_ai_core.adapters.outbound.openai.llm import OpenAILLMProvider
from foldmind_ai_core.adapters.outbound.openai.settings import OpenAISettings
from foldmind_ai_core.core.application.models.llm import LLMMessage
from foldmind_ai_core.shared.validation import InvalidInputError


@dataclass(slots=True)
class FakeEmbedding:
    index: int
    embedding: list[float]


@dataclass(slots=True)
class FakeEmbeddingResponse:
    data: list[FakeEmbedding]


@dataclass(slots=True)
class FakeTextResponse:
    output_text: str


class FakeResponsesAPI:
    def __init__(self, response: FakeTextResponse) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> FakeTextResponse:
        self.calls.append(kwargs)
        return self.response


class FakeEmbeddingsAPI:
    def __init__(self, response: FakeEmbeddingResponse) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> FakeEmbeddingResponse:
        self.calls.append(kwargs)
        return self.response


class FakeOpenAISDK:
    def __init__(
        self,
        *,
        text_response: FakeTextResponse | None = None,
        embedding_response: FakeEmbeddingResponse | None = None,
    ) -> None:
        self.responses = FakeResponsesAPI(text_response or FakeTextResponse("ok"))
        self.embeddings = FakeEmbeddingsAPI(
            embedding_response
            or FakeEmbeddingResponse(
                [
                    FakeEmbedding(index=0, embedding=[0.1, 0.2]),
                    FakeEmbedding(index=1, embedding=[0.3, 0.4]),
                ]
            )
        )


class OpenAIProviderTests(unittest.TestCase):
    def test_openai_settings_reject_malformed_retry_and_timeout_values(self) -> None:
        with self.assertRaises(InvalidInputError):
            OpenAISettings(api_key=" ")
        with self.assertRaises(InvalidInputError):
            OpenAISettings(api_key="test-key", base_url=" ")
        with self.assertRaises(InvalidInputError):
            OpenAISettings(api_key="test-key", timeout_seconds=float("nan"))
        with self.assertRaises(InvalidInputError):
            OpenAISettings(api_key="test-key", timeout_seconds=True)
        with self.assertRaises(InvalidInputError):
            OpenAISettings(api_key="test-key", max_retries=True)
        with self.assertRaises(InvalidInputError):
            OpenAISettings(api_key="test-key", max_retries=-1)

        settings = OpenAISettings(
            api_key=" test-key ",
            base_url=" https://api.openai.test ",
        )
        self.assertEqual(settings.api_key, "test-key")
        self.assertEqual(settings.base_url, "https://api.openai.test")

    def test_llm_maps_messages_to_responses_api_and_returns_output_text(self) -> None:
        sdk_client = FakeOpenAISDK(text_response=FakeTextResponse("generated text"))
        llm = OpenAILLMProvider(model="gpt-5", client=_openai_client(sdk_client))

        result = llm.generate(
            [
                LLMMessage(role="system", content="system prompt"),
                LLMMessage(role="user", content="user request"),
            ]
        )

        self.assertEqual(result, "generated text")
        self.assertEqual(sdk_client.responses.calls[0]["model"], "gpt-5")
        self.assertEqual(
            sdk_client.responses.calls[0]["input"],
            [
                {"role": "system", "content": "system prompt"},
                {"role": "user", "content": "user request"},
            ],
        )

    def test_llm_rejects_empty_output_text(self) -> None:
        llm = OpenAILLMProvider(
            model="gpt-5",
            client=_openai_client(FakeOpenAISDK(text_response=FakeTextResponse(""))),
        )

        with self.assertRaisesRegex(AIProviderError, "non-empty output_text"):
            llm.generate([LLMMessage(role="user", content="hello")])

    def test_llm_rejects_malformed_text_response(self) -> None:
        sdk_client = FakeOpenAISDK(text_response=FakeTextResponse("unused"))
        sdk_client.responses.response = object()
        llm = OpenAILLMProvider(model="gpt-5", client=_openai_client(sdk_client))

        with self.assertRaisesRegex(AIProviderError, "output_text"):
            llm.generate([LLMMessage(role="user", content="hello")])

    def test_embedding_provider_preserves_input_order_and_dimensions(self) -> None:
        sdk_client = FakeOpenAISDK(
            embedding_response=FakeEmbeddingResponse(
                [
                    FakeEmbedding(index=1, embedding=[0.3, 0.4]),
                    FakeEmbedding(index=0, embedding=[0.1, 0.2]),
                ]
            )
        )
        embeddings = OpenAIEmbeddingProvider(
            model="text-embedding-3-small",
            dimensions=1536,
            client=_openai_client(sdk_client),
        )

        vectors = embeddings.embed_texts(["first", "second"])

        self.assertEqual(vectors, [[0.1, 0.2], [0.3, 0.4]])
        self.assertEqual(sdk_client.embeddings.calls[0]["model"], "text-embedding-3-small")
        self.assertEqual(sdk_client.embeddings.calls[0]["input"], ["first", "second"])
        self.assertEqual(sdk_client.embeddings.calls[0]["encoding_format"], "float")
        self.assertEqual(sdk_client.embeddings.calls[0]["dimensions"], 1536)

    def test_embedding_provider_rejects_empty_input_and_count_mismatch(self) -> None:
        embeddings = OpenAIEmbeddingProvider(
            model="text-embedding-3-small",
            client=_openai_client(
                FakeOpenAISDK(embedding_response=FakeEmbeddingResponse([]))
            ),
        )

        with self.assertRaisesRegex(InvalidInputError, "texts must not be empty"):
            embeddings.embed_texts([])
        with self.assertRaisesRegex(AIProviderError, "returned 0 embeddings"):
            embeddings.embed_texts(["first"])

    def test_embedding_provider_rejects_malformed_dimensions_and_indexes(self) -> None:
        with self.assertRaisesRegex(InvalidInputError, "positive integer"):
            OpenAIEmbeddingProvider(
                model="text-embedding-3-small",
                dimensions=True,
                client=_openai_client(FakeOpenAISDK()),
            )

        embeddings = OpenAIEmbeddingProvider(
            model="text-embedding-3-small",
            client=_openai_client(
                FakeOpenAISDK(
                    embedding_response=FakeEmbeddingResponse(
                        [FakeEmbedding(index=True, embedding=[0.1])]
                    )
                )
            ),
        )

        with self.assertRaisesRegex(AIProviderError, "index"):
            embeddings.embed_texts(["first"])

    def test_embedding_provider_rejects_non_finite_vector_values(self) -> None:
        embeddings = OpenAIEmbeddingProvider(
            model="text-embedding-3-small",
            client=_openai_client(
                FakeOpenAISDK(
                    embedding_response=FakeEmbeddingResponse(
                        [FakeEmbedding(index=0, embedding=[0.1, float("nan")])]
                    )
                )
            ),
        )

        with self.assertRaisesRegex(AIProviderError, "finite numbers"):
            embeddings.embed_texts(["first"])

    def test_embedding_provider_rejects_malformed_response_items(self) -> None:
        embeddings = OpenAIEmbeddingProvider(
            model="text-embedding-3-small",
            client=_openai_client(
                FakeOpenAISDK(
                    embedding_response=FakeEmbeddingResponse([{"embedding": [0.1]}])
                )
            ),
        )

        with self.assertRaisesRegex(AIProviderError, "malformed"):
            embeddings.embed_texts(["first"])


def _openai_client(sdk_client: FakeOpenAISDK) -> OpenAIClient:
    return OpenAIClient(
        settings=OpenAISettings(api_key="test-key"),
        sdk_client=sdk_client,
    )


if __name__ == "__main__":
    unittest.main()
