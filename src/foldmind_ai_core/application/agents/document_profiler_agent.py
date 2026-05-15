from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from foldmind_ai_core.application.dto.llm import LLMMessage
from foldmind_ai_core.application.ports.outbound.llm import LLM
from foldmind_ai_core.application.ports.outbound.prompt_repository import PromptRepositoryPort
from foldmind_ai_core.application.services.prompts import PROMPT_DOCUMENT_PROFILING
from foldmind_ai_core.domain.common import Confidence
from foldmind_ai_core.domain.indexing.chunks import DocumentChunk
from foldmind_ai_core.domain.profiling.models import DocumentProfile
from foldmind_ai_core.domain.profiling.concepts import profile_concepts_from_labels
from foldmind_ai_core.domain.reference.documents import SourceDocument


@dataclass(slots=True)
class DocumentProfilerAgent:
    llm: LLM
    prompt_repository: PromptRepositoryPort
    profile_version: str
    profile_schema_version: str
    prompt_version: str
    model: str

    def profile(self, document: SourceDocument, chunks: list[DocumentChunk]) -> DocumentProfile:
        raw = self._generate(document, chunks)
        parsed = self._parse_json(raw)
        if parsed is None:
            return self._fallback_profile(document, chunks)
        return self._profile_from_payload(document, chunks, parsed)

    def _generate(self, document: SourceDocument, chunks: list[DocumentChunk]) -> str:
        system = self.prompt_repository.get(PROMPT_DOCUMENT_PROFILING)
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

    def _parse_json(self, raw: str) -> dict[str, Any] | None:
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return value if isinstance(value, dict) else None

    def _profile_from_payload(
        self,
        document: SourceDocument,
        chunks: list[DocumentChunk],
        payload: dict[str, Any],
    ) -> DocumentProfile:
        fallback = self._fallback_profile(document, chunks)
        return DocumentProfile(
            tenant=document.tenant,
            document_type=document.document_type,
            document_id=document.document_id,
            source_version=document.source_version,
            title=document.title or document.document_id,
            summary=str(payload.get("summary") or fallback.summary),
            profile_version=str(payload.get("profile_version") or self.profile_version),
            concepts=self._concepts(document, payload) or fallback.concepts,
            profile_schema_version=str(
                payload.get("profile_schema_version") or self.profile_schema_version
            ),
            profile_confidence=float(
                payload.get("confidence")
                if payload.get("confidence") is not None
                else fallback.profile_confidence or 1.0
            ),
            model=str(payload.get("model") or self.model),
            prompt_version=str(payload.get("prompt_version") or self.prompt_version),
            metadata={
                "source_metadata": dict(document.metadata),
            },
        )

    def _fallback_profile(
        self,
        document: SourceDocument,
        chunks: list[DocumentChunk],
    ) -> DocumentProfile:
        text = document.full_text
        summary = text[:500] if text else document.title or document.document_id
        title_terms = tuple(document.title.split())
        document_terms = tuple(dict.fromkeys(title_terms))[:12]
        title_concepts = (document.title.strip(),) if document.title.strip() else ()
        concept_labels = document_terms[:5] or title_concepts
        return DocumentProfile(
            tenant=document.tenant,
            document_type=document.document_type,
            document_id=document.document_id,
            source_version=document.source_version,
            title=document.title or document.document_id,
            summary=summary or "Unprofiled document.",
            profile_version=self.profile_version,
            concepts=profile_concepts_from_labels(
                tenant=document.tenant,
                labels=concept_labels,
                confidence=Confidence(0.5),
            ),
            profile_schema_version=self.profile_schema_version,
            profile_confidence=0.5,
            model=self.model,
            prompt_version=self.prompt_version,
            metadata={
                "source_metadata": dict(document.metadata),
            },
        )

    def _concepts(self, document: SourceDocument, payload: dict[str, Any]):
        concept_values = payload.get("concepts")
        if not isinstance(concept_values, list | tuple):
            return ()
        labels = tuple(
            str(item.get("label") if isinstance(item, dict) else item).strip()
            for item in concept_values
            if str(item.get("label") if isinstance(item, dict) else item).strip()
        )
        if not labels:
            return ()
        return profile_concepts_from_labels(
            tenant=document.tenant,
            labels=labels,
            confidence=(
                float(payload["confidence"])
                if payload.get("confidence") is not None
                else None
            ),
        )
