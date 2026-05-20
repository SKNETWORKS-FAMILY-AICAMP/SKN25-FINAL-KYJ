from __future__ import annotations

from typing import Any

from pydantic import Field

from foldmind_ai_core.adapters.inbound.http.dtos.dto_model import APIDTO

class RetrievalResultDTO(APIDTO):
    tenant: str
    document_type: str | None
    document_id: str
    source_version: str
    created_at: str = ""
    updated_at: str = ""
    chunk_id: str
    chunk_index: int
    text: str
    score: float
    start_offset: int
    end_offset: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class GeneratedTextResponse(APIDTO):
    text: str
    citations: list[RetrievalResultDTO] = Field(default_factory=list)


class FolderRecommendationDTO(APIDTO):
    folder_id: str
    reason: str
    score: float
