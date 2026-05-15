from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.domain.profiling.models import DocumentProfile


class ProfileRepository(Protocol):
    def upsert(self, profile: DocumentProfile) -> None:
        ...

    def get_document_profile(
        self,
        *,
        document_id: str,
    ) -> DocumentProfile | None:
        ...

    def delete_document_profile(
        self,
        *,
        document_id: str,
    ) -> None:
        ...
