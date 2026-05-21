from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from foldmind_ai_core.core.application.agents.json_output import parse_json_object_output
from foldmind_ai_core.core.application.errors import InvalidAgentOutputError
from foldmind_ai_core.core.application.models.llm import LLMMessage
from foldmind_ai_core.core.application.ports.outbound.llm import LLMProvider
from foldmind_ai_core.core.application.ports.outbound.prompt_store import PromptStore
from foldmind_ai_core.core.application.services.prompts import PROMPT_DOCUMENT_PROFILING
from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.profiling import (
    DocumentSignal,
    DocumentSignalType,
    DocumentProfile,
    DocumentSignalExtraction,
    SignalEvidence,
)
from foldmind_ai_core.core.domain.models.reference.documents import SourceDocument
from foldmind_ai_core.core.domain.services.profiling import (
    DEFAULT_SIGNAL_DEFINITIONS,
    DocumentSignalInput,
    create_document_signal,
)
from foldmind_ai_core.shared.types import JsonObject
from foldmind_ai_core.shared.validation import InvalidInputError


@dataclass(slots=True)
class DocumentProfilerAgent:
    llm: LLMProvider
    prompt_store: PromptStore
    prompt_version: str
    model: str

    def __post_init__(self) -> None:
        for field_name in (
            "prompt_version",
            "model",
        ):
            if not getattr(self, field_name).strip():
                raise InvalidInputError(f"{field_name} must not be blank.")

    def profile(
        self,
        document: SourceDocument,
        chunks: list[DocumentChunk],
    ) -> DocumentSignalExtraction:
        raw = self._generate(document, chunks)
        try:
            parsed = parse_json_object_output(raw)
        except ValueError:
            raise InvalidAgentOutputError(
                "Document profiler response must be a JSON object."
            ) from None

        document_index_input_digest = _document_index_input_digest(chunks)
        document_signal_input_digest = DocumentSignalInput(
            document_index_input_digest=document_index_input_digest,
            signal_generation_version=self.prompt_version,
        ).digest
        profile = DocumentProfile(
            tenant=document.tenant,
            document_type=document.document_type,
            document_id=document.document_id,
            source_version=document.source_version,
            document_index_input_digest=document_index_input_digest,
            document_signal_input_digest=document_signal_input_digest,
            created_at=document.created_at,
            updated_at=document.updated_at,
            title=document.title.strip() or document.document_id,
            metadata={
                "source_metadata": dict(document.metadata),
            },
            signal_generation_version=self.prompt_version,
        )
        signals = self._signals(
            document=document,
            chunks=chunks,
            document_signal_input_digest=document_signal_input_digest,
            payload=parsed,
        )
        return DocumentSignalExtraction(profile=profile, signals=signals)

    def _generate(self, document: SourceDocument, chunks: list[DocumentChunk]) -> str:
        system = self.prompt_store.get(PROMPT_DOCUMENT_PROFILING)
        chunk_payload = [
            {
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "start_offset": chunk.start_offset,
                "end_offset": chunk.end_offset,
            }
            for chunk in chunks
        ]
        return self.llm.generate(
            [
                LLMMessage(role="system", content=system),
                LLMMessage(
                    role="user",
                    content=json.dumps(
                        {
                            "title": document.title,
                            "body": document.body,
                            "chunks": chunk_payload,
                        },
                        ensure_ascii=False,
                    ),
                ),
            ]
        )

    def _signals(
        self,
        *,
        document: SourceDocument,
        chunks: list[DocumentChunk],
        document_signal_input_digest: str,
        payload: JsonObject,
    ) -> tuple[DocumentSignal, ...]:
        values = payload.get("signals")
        if not isinstance(values, list | tuple):
            raise InvalidAgentOutputError(
                "Document profiler response must include signals."
            )
        if not values:
            raise InvalidAgentOutputError(
                "Document profiler response must include at least one signal."
            )
        chunk_ids = {chunk.chunk_id for chunk in chunks}
        signals = tuple(
            self._signal(
                document=document,
                chunk_ids=chunk_ids,
                document_signal_input_digest=document_signal_input_digest,
                payload=item,
            )
            for item in values
        )
        summary_count = sum(
            1
            for signal in signals
            if signal.signal_type == DocumentSignalType.SUMMARY
        )
        if summary_count != 1:
            raise InvalidAgentOutputError(
                "Document profiler response must include exactly one summary signal."
            )
        signal_ids = [signal.signal_id for signal in signals]
        if len(signal_ids) != len(set(signal_ids)):
            raise InvalidAgentOutputError(
                "Document profiler response must not include duplicate signals."
            )
        return signals

    def _signal(
        self,
        *,
        document: SourceDocument,
        chunk_ids: set[str],
        document_signal_input_digest: str,
        payload: object,
    ) -> DocumentSignal:
        signal_payload = self._json_object(payload, "signal")
        signal_type = self._signal_type(signal_payload)
        text = self._required_text(signal_payload, "text")
        evidence = self._evidence(signal_payload, chunk_ids)
        return create_document_signal(
            tenant=document.tenant,
            document_type=document.document_type,
            document_id=document.document_id,
            source_version=document.source_version,
            document_signal_input_digest=document_signal_input_digest,
            signal_generation_version=self.prompt_version,
            signal_type=signal_type,
            text=text,
            attributes=self._optional_json_object(
                signal_payload.get("attributes"),
                "signal attributes",
            ),
            evidence=evidence,
            confidence=self._required_confidence(signal_payload, "confidence"),
            extractor_name="document_profiler",
            extractor_version=self.prompt_version,
            generation_model=self.model,
            metadata=self._optional_json_object(
                signal_payload.get("metadata"),
                "signal metadata",
            ),
        )

    def _signal_type(self, payload: Mapping[str, object]) -> DocumentSignalType:
        value = self._required_text(payload, "type")
        try:
            return DEFAULT_SIGNAL_DEFINITIONS.require(value)
        except InvalidInputError as exc:
            raise InvalidAgentOutputError(str(exc)) from exc

    def _evidence(
        self,
        payload: Mapping[str, object],
        chunk_ids: set[str],
    ) -> tuple[SignalEvidence, ...]:
        values = payload.get("evidence")
        if not isinstance(values, list | tuple) or not values:
            raise InvalidAgentOutputError(
                "Document profiler signals must include non-empty evidence."
            )
        evidence: list[SignalEvidence] = []
        for item in values:
            evidence_payload = self._json_object(item, "evidence")
            signal_evidence = self._signal_evidence(evidence_payload)
            if signal_evidence.chunk_id not in chunk_ids:
                raise InvalidAgentOutputError(
                    "Document profiler signal evidence chunk_id must refer to a provided chunk."
                )
            evidence.append(signal_evidence)
        return tuple(evidence)

    def _signal_evidence(self, payload: Mapping[str, object]) -> SignalEvidence:
        start_offset = self._optional_offset(payload.get("start_offset"), "start_offset")
        end_offset = self._optional_offset(payload.get("end_offset"), "end_offset")
        if (
            start_offset is not None
            and end_offset is not None
            and end_offset < start_offset
        ):
            raise InvalidAgentOutputError(
                "Document profiler evidence end_offset must be greater than or equal to start_offset."
            )
        return SignalEvidence(
            chunk_id=self._required_text(payload, "chunk_id"),
            quote=self._required_text(payload, "quote"),
            start_offset=start_offset,
            end_offset=end_offset,
            metadata=self._optional_json_object(
                payload.get("metadata"),
                "evidence metadata",
            ),
        )

    def _required_text(self, payload: Mapping[str, object], name: str) -> str:
        value = payload.get(name)
        if not isinstance(value, str) or not value.strip():
            raise InvalidAgentOutputError(
                f"Document profiler response must include {name}."
            )
        return value.strip()

    def _required_confidence(
        self,
        payload: Mapping[str, object],
        name: str,
    ) -> float:
        value = payload.get(name)
        if value is None:
            raise InvalidAgentOutputError(
                f"Document profiler response must include {name}."
            )
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise InvalidAgentOutputError(
                f"Document profiler {name} must be numeric."
            )
        confidence = float(value)
        if not math.isfinite(confidence) or confidence < 0.0 or confidence > 1.0:
            raise InvalidAgentOutputError(
                f"Document profiler {name} must be between 0 and 1."
            )
        return confidence

    def _optional_offset(self, value: object, name: str) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise InvalidAgentOutputError(
                f"Document profiler evidence {name} must be a non-negative integer."
            )
        return value

    def _json_object(self, value: object, name: str) -> JsonObject:
        if not isinstance(value, Mapping):
            raise InvalidAgentOutputError(
                f"Document profiler {name} must be a JSON object."
            )
        return cast(JsonObject, dict(value))

    def _optional_json_object(self, value: object, name: str) -> JsonObject:
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise InvalidAgentOutputError(
                f"Document profiler {name} must be a JSON object."
            )
        return cast(JsonObject, dict(value))


def _document_index_input_digest(chunks: list[DocumentChunk]) -> str:
    if not chunks:
        raise InvalidAgentOutputError("Document profiler requires at least one chunk.")
    return chunks[0].document_index_input_digest
