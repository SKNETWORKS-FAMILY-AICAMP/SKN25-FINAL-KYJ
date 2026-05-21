from __future__ import annotations

from typing import Any

_CONSTRAINTS = (
    "CREATE CONSTRAINT document_identity IF NOT EXISTS "
    "FOR (n:Document) REQUIRE n.document_id IS UNIQUE",
    "CREATE CONSTRAINT folder_identity IF NOT EXISTS "
    "FOR (n:Folder) REQUIRE n.folder_id IS UNIQUE",
    "CREATE CONSTRAINT document_signal_identity IF NOT EXISTS "
    "FOR (n:DocumentSignal) REQUIRE n.signal_id IS UNIQUE",
    "CREATE CONSTRAINT folder_signal_identity IF NOT EXISTS "
    "FOR (n:FolderSignal) REQUIRE n.signal_id IS UNIQUE",
)

_INDEXES = (
    "CREATE INDEX document_tenant IF NOT EXISTS "
    "FOR (n:Document) ON (n.tenant)",
    "CREATE INDEX document_tenant_type IF NOT EXISTS "
    "FOR (n:Document) ON (n.tenant, n.document_type)",
    "CREATE INDEX document_created_at IF NOT EXISTS "
    "FOR (n:Document) ON (n.created_at)",
    "CREATE INDEX document_updated_at IF NOT EXISTS "
    "FOR (n:Document) ON (n.updated_at)",
    "CREATE INDEX folder_tenant IF NOT EXISTS "
    "FOR (n:Folder) ON (n.tenant)",
    "CREATE INDEX folder_projection_state IF NOT EXISTS "
    "FOR (n:Folder) ON (n.projection_state)",
    "CREATE INDEX folder_parent IF NOT EXISTS "
    "FOR (n:Folder) ON (n.parent_folder_id)",
    "CREATE INDEX folder_index_input_digest IF NOT EXISTS "
    "FOR (n:Folder) ON (n.folder_index_input_digest)",
    "CREATE INDEX document_signal_lookup IF NOT EXISTS "
    "FOR (n:DocumentSignal) ON (n.tenant, n.signal_type)",
    "CREATE INDEX folder_signal_lookup IF NOT EXISTS "
    "FOR (n:FolderSignal) ON (n.tenant, n.folder_id, n.signal_type)",
)

_FULLTEXT_INDEXES = (
    "CREATE FULLTEXT INDEX document_graph_text IF NOT EXISTS "
    "FOR (n:Document|DocumentSignal) ON EACH [n.label, n.text, n.signal_key]",
    "CREATE FULLTEXT INDEX folder_graph_text IF NOT EXISTS "
    "FOR (n:Folder|FolderSignal) ON EACH [n.label, n.description, n.text, n.signal_key]",
)


def ensure_neo4j_schema(session: Any) -> None:
    for statement in (*_CONSTRAINTS, *_INDEXES, *_FULLTEXT_INDEXES):
        session.run(statement)
