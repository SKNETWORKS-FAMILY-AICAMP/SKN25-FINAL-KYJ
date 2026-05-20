from __future__ import annotations

import math
from dataclasses import dataclass, field

from foldmind_ai_core.core.domain.models.retrieval.results import (
    FolderRetrievalResult,
    RetrievedFolder,
)


@dataclass(slots=True)
class FolderRetrievalRanker:
    top_k: int
    excluded_folder_ids: tuple[str, ...] = ()
    _folder_scores: dict[str, _FolderScore] = field(default_factory=dict, init=False)
    _document_signals: dict[str, _DocumentFolderSignal] = field(
        default_factory=dict,
        init=False,
    )

    @property
    def document_ids(self) -> tuple[str, ...]:
        return tuple(self._document_signals)

    def add_folder_score(
        self,
        *,
        folder: RetrievedFolder,
        score: float,
        reason: str,
    ) -> None:
        if not folder.folder_id.strip() or not math.isfinite(score):
            return
        item = self._folder_scores.setdefault(
            folder.folder_id,
            _FolderScore(folder=folder),
        )
        item.add(score, reason)

    def add_document_signal(
        self,
        *,
        document_id: str,
        score: float,
        reason: str,
    ) -> None:
        if not document_id.strip() or not math.isfinite(score):
            return
        item = self._document_signals.setdefault(
            document_id,
            _DocumentFolderSignal(),
        )
        item.add(score, reason)

    def add_document_folders(
        self,
        folders_by_document: dict[str, tuple[RetrievedFolder, ...]],
    ) -> None:
        for document_id, signal in self._document_signals.items():
            seen_folder_ids: set[str] = set()
            for folder in folders_by_document.get(document_id, ()):
                folder_id = folder.folder_id.strip()
                if not folder_id or folder_id in seen_folder_ids:
                    continue
                seen_folder_ids.add(folder_id)
                self.add_folder_score(
                    folder=folder,
                    score=signal.score,
                    reason=" ".join(sorted(signal.reasons)),
                )

    def results(self) -> list[FolderRetrievalResult]:
        ranked = sorted(
            self._folder_scores.values(),
            key=lambda item: item.score,
            reverse=True,
        )
        return [
            FolderRetrievalResult(
                folder=item.folder,
                score=item.score,
                reason=" ".join(sorted(item.reasons)),
            )
            for item in ranked
            if item.folder.folder_id not in self.excluded_folder_ids
        ][: self.top_k]


@dataclass(slots=True)
class _FolderScore:
    folder: RetrievedFolder
    score: float = 0.0
    reasons: set[str] = field(default_factory=set)

    def add(self, score: float, reason: str) -> None:
        self.score += score
        if reason:
            self.reasons.add(reason)


@dataclass(slots=True)
class _DocumentFolderSignal:
    score: float = 0.0
    reasons: set[str] = field(default_factory=set)

    def add(self, score: float, reason: str) -> None:
        self.score = max(self.score, score)
        if reason:
            self.reasons.add(reason)
