from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DocumentIndexState:
    document_id: str
    document_index_input_digest: str
    document_signal_input_digest: str
    signal_generation_version: str = "1"
