from __future__ import annotations

from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from foldmind_ai_core.adapters.outbound.postgres.models.base import (
    CreatedAndUpdatedAtColumns,
    PostgresOrmBase,
)


class VectorProjectionRecordRow(CreatedAndUpdatedAtColumns, PostgresOrmBase):
    __tablename__ = "vector_projection_records"

    tenant_id: Mapped[str] = mapped_column(Text, nullable=False)
    collection_name: Mapped[str] = mapped_column(Text, primary_key=True)
    point_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    source_kind: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[str] = mapped_column(Text, nullable=False)
    vector_item_kind: Mapped[str] = mapped_column(Text, nullable=False)
    vector_item_id: Mapped[str] = mapped_column(Text, nullable=False)
    source_input_digest: Mapped[str] = mapped_column(Text, nullable=False)
    vector_input_digest: Mapped[str] = mapped_column(Text, nullable=False)
