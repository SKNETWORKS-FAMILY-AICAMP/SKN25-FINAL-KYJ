"""create normalized task storage

Revision ID: 20260513_0002
Revises: 20260513_0001
Create Date: 2026-05-13
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from alembic import op

revision = "20260513_0002"
down_revision = "20260513_0001"
branch_labels = None
depends_on = None

SqlFile = tuple[str, str]

SQL_DIR = Path(__file__).resolve().parents[1] / "sql" / "20260513_0002_create_task_storage"


def upgrade() -> None:
    execute_sql_files(SCHEMA_SQL_FILES)


def downgrade() -> None:
    for table_name in DOWNGRADE_TABLES:
        op.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")


def execute_sql_files(files: Iterable[SqlFile]) -> None:
    for _, file_name in files:
        op.execute((SQL_DIR / file_name).read_text(encoding="utf-8"))


SCHEMA_SQL_FILES: tuple[SqlFile, ...] = (
    ("task core", "00_task_core.sql"),
    ("host actions", "10_host_actions.sql"),
    ("task events", "20_task_events.sql"),
)

DOWNGRADE_TABLES = (
    "host_actions",
    "task_events",
    "task_job_results",
    "task_jobs",
    "task_inputs",
    "tasks",
)
