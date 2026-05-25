from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VectorProjectionState:
    tenant: str
    collection_name: str
    point_id: str
    source_kind: str
    source_id: str
    vector_item_kind: str
    vector_item_id: str
    source_input_digest: str
    vector_input_digest: str
