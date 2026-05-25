from __future__ import annotations

from foldmind_ai_core.adapters.outbound.postgres.models.vector_projection_ledger import (
    VectorProjectionRecordRow,
)
from foldmind_ai_core.core.domain.models.vector_projection_state import (
    VectorProjectionState,
)


def vector_projection_record_row(record: VectorProjectionState) -> VectorProjectionRecordRow:
    return VectorProjectionRecordRow(
        tenant_id=record.tenant,
        collection_name=record.collection_name,
        point_id=record.point_id,
        source_kind=record.source_kind,
        source_id=record.source_id,
        vector_item_kind=record.vector_item_kind,
        vector_item_id=record.vector_item_id,
        source_input_digest=record.source_input_digest,
        vector_input_digest=record.vector_input_digest,
    )
