"""create initial projection storage

Revision ID: 20260513_0001
Revises:
Create Date: 2026-05-13
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from alembic import op

revision = "20260513_0001"
down_revision = None
branch_labels = None
depends_on = None

SqlFile = tuple[str, str]

SQL_DIR = Path(__file__).resolve().parents[1] / "sql" / "20260513_0001_create_projection_storage"


def upgrade() -> None:
    execute_sql_files(SCHEMA_SQL_FILES)
    create_updated_at_triggers(UPDATED_AT_TABLES)
    execute_sql_files(INDEX_SQL_FILES)


def downgrade() -> None:
    for table_name in DOWNGRADE_TABLES:
        op.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")


def execute_sql_files(files: Iterable[SqlFile]) -> None:
    for _, file_name in files:
        op.execute((SQL_DIR / file_name).read_text(encoding="utf-8"))


def create_updated_at_triggers(table_names: Iterable[str]) -> None:
    for table_name in table_names:
        op.execute(
            f"""
CREATE TRIGGER {table_name}_set_updated_at
    BEFORE UPDATE ON {table_name}
    FOR EACH ROW EXECUTE FUNCTION moddatetime(updated_at);
"""
        )


SCHEMA_SQL_FILES: tuple[SqlFile, ...] = (
    ("postgres extensions", "00_extensions.sql"),
    ("tenant and source snapshots", "10_tenant_and_source_snapshots.sql"),
    ("source document folder relations", "15_source_document_folder_relations.sql"),
    ("document projections", "20_document_projections.sql"),
    ("folder projections", "30_folder_projections.sql"),
    ("vector projection ledger", "40_vector_projection_ledger.sql"),
    ("projection outbox", "50_projection_outbox.sql"),
)

INDEX_SQL_FILES: tuple[SqlFile, ...] = (
    ("projection lookup indexes", "90_projection_lookup_indexes.sql"),
)

UPDATED_AT_TABLES = (
    "tenant_storage_scopes",
    "document_sources",
    "source_document_folder_relations",
    "folder_sources",
    "document_index_records",
    "document_chunks",
    "document_signals",
    "folder_index_records",
    "folder_signals",
    "vector_projection_records",
)

DOWNGRADE_TABLES = (
    "outbox_events",
    "vector_projection_records",
    "folder_signals",
    "folder_index_records",
    "document_signals",
    "document_chunks",
    "document_index_records",
    "source_document_folder_relations",
    "folder_sources",
    "document_sources",
    "tenant_storage_scopes",
)
