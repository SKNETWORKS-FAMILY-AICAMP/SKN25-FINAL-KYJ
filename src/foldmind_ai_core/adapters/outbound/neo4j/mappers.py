from __future__ import annotations

import json
from typing import Any

from foldmind_ai_core.domain.retrieval.queries import SearchScope
from foldmind_ai_core.domain.retrieval.results import RetrievedDocument


def document_from_node(node: Any) -> RetrievedDocument:
    return RetrievedDocument(
        tenant=str(node["tenant"]),
        document_type=str(node.get("document_type") or "document"),
        document_id=str(node["document_id"]),
        source_version=str(node.get("source_version") or ""),
        metadata=json_dict(node.get("metadata_json")),
    )


def matches_scope(document: RetrievedDocument, scope: SearchScope | None) -> bool:
    if scope is None:
        return True
    if scope.document_type is not None and document.document_type != scope.document_type:
        return False
    if scope.document_id is not None and document.document_id != scope.document_id:
        return False
    if scope.document_ids and document.document_id not in scope.document_ids:
        return False
    for key, value in scope.metadata_filter.items():
        if document.metadata.get(key) != value:
            return False
    return True


def json_dict(value: object) -> dict[str, Any]:
    if not isinstance(value, str) or not value:
        return {}
    parsed = json.loads(value)
    return parsed if isinstance(parsed, dict) else {}
