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


def ensure_neo4j_schema(session: Any) -> None:
    for statement in _CONSTRAINTS:
        session.run(statement)
