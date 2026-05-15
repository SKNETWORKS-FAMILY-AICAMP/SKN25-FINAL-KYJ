from __future__ import annotations

from typing import Any

_CONSTRAINTS = (
    "CREATE CONSTRAINT document_identity IF NOT EXISTS "
    "FOR (n:Document) REQUIRE n.document_id IS UNIQUE",
    "CREATE CONSTRAINT folder_identity IF NOT EXISTS "
    "FOR (n:Folder) REQUIRE n.folder_id IS UNIQUE",
    "CREATE CONSTRAINT tag_identity IF NOT EXISTS "
    "FOR (n:Tag) REQUIRE n.tag_id IS UNIQUE",
    "CREATE CONSTRAINT concept_identity IF NOT EXISTS "
    "FOR (n:Concept) REQUIRE n.concept_id IS UNIQUE",
    "CREATE CONSTRAINT concept_tenant_key IF NOT EXISTS "
    "FOR (n:Concept) REQUIRE (n.tenant, n.concept_key) IS UNIQUE",
)


def ensure_schema(session: Any) -> None:
    for statement in _CONSTRAINTS:
        session.run(statement)
