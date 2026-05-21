from __future__ import annotations

import math
from typing import Any

from foldmind_ai_core.adapters.outbound.neo4j.mappers import (
    document_from_node,
    matches_scope,
)
from foldmind_ai_core.core.application.queries.retrieval import SearchScope
from foldmind_ai_core.core.application.queries.scope_matching import (
    sort_by_timestamp_scope,
)
from foldmind_ai_core.core.domain.models.retrieval.results import (
    DocumentRetrievalResult,
    RetrievedDocument,
    RetrievedFolder,
)

_SIGNAL_WEIGHTS = {
    "DOCUMENT_TITLE": 0.8,
    "HAS_SIGNAL": 0.75,
    "IN_FOLDER": 0.75,
    "FOLDER_DESCENDANT": 0.55,
    "FOLDER_SIBLING": 0.35,
}


def graph_search(
    session: Any,
    *,
    tenant: str,
    query_text: str,
    top_k: int,
    scope: SearchScope | None,
) -> list[DocumentRetrievalResult]:
    query = query_text.casefold()
    scoped_document_ids = _scoped_document_ids(session, tenant=tenant, scope=scope)
    if scope is not None and scope.folder_ids and not scoped_document_ids:
        return []

    scores: dict[str, float] = {}
    documents: dict[str, RetrievedDocument] = {}
    for cypher, signal_type in _graph_search_queries():
        records = session.run(
            cypher,
            tenant=tenant,
            query=query,
            document_ids=list(scoped_document_ids),
        )
        for record in records:
            try:
                document = document_from_node(record["d"])
            except (KeyError, TypeError, ValueError):
                continue
            if not matches_scope(document, scope):
                continue
            if scoped_document_ids and document.document_id not in scoped_document_ids:
                continue
            key = document.document_id
            confidence = _relationship_confidence(record.get("confidence"))
            if confidence is None:
                continue
            if confidence <= 0.0:
                continue
            scores[key] = scores.get(key, 0.0) + (
                _SIGNAL_WEIGHTS[signal_type] * confidence
            )
            documents[key] = document
    ranked = [
        DocumentRetrievalResult(document=documents[key], score=score)
        for key, score in scores.items()
    ]
    ranked.sort(key=lambda result: result.score, reverse=True)
    ranked = sort_by_timestamp_scope(
        ranked,
        scope=scope,
        timestamp_value=lambda result, field: getattr(result.document, field),
    )
    return ranked[:top_k]


def document_ids_for_scope(
    session: Any,
    *,
    tenant: str,
    scope: SearchScope,
) -> tuple[str, ...]:
    return tuple(sorted(_scoped_document_ids(session, tenant=tenant, scope=scope)))


def folders_for_documents(
    session: Any,
    *,
    tenant: str,
    document_ids: tuple[str, ...],
) -> dict[str, tuple[RetrievedFolder, ...]]:
    if not document_ids:
        return {}
    records = session.run(
        """
        MATCH (d:Document)-[r:IN_FOLDER]->(f:Folder)
        WHERE d.tenant = $tenant
          AND r.tenant = $tenant
          AND f.tenant = $tenant
          AND d.document_id IN $document_ids
          AND coalesce(f.projection_state, 'reference') <> 'deleted'
        RETURN d.document_id AS document_id,
               collect(DISTINCT {
                   tenant: r.tenant,
                   folder_id: f.folder_id,
                   source_version: f.source_version,
                   created_at: f.created_at,
                   updated_at: f.updated_at
               }) AS folders
        """,
        tenant=tenant,
        document_ids=list(document_ids),
    )
    folders_by_document: dict[str, tuple[RetrievedFolder, ...]] = {}
    for record in records:
        document_id = _record_text(record, "document_id")
        if not document_id:
            continue
        folders_by_document[document_id] = _folders_from_records(record.get("folders", ()))
    return folders_by_document


def _scoped_document_ids(
    session: Any,
    *,
    tenant: str,
    scope: SearchScope | None,
) -> set[str]:
    if scope is None:
        return set()
    candidate_sets: list[set[str]] = []
    explicit_ids = set(scope.document_ids)
    if scope.document_id is not None:
        explicit_ids.add(scope.document_id)
    if explicit_ids:
        candidate_sets.append(explicit_ids)
    if scope.folder_ids:
        candidate_sets.append(
            _query_document_ids(
                session,
                """
                MATCH (d:Document)-[r:IN_FOLDER]->(f:Folder)
                WHERE d.tenant = $tenant
                  AND r.tenant = $tenant
                  AND f.tenant = $tenant
                  AND f.folder_id IN $values
                  AND coalesce(f.projection_state, 'reference') <> 'deleted'
                RETURN DISTINCT d.document_id AS document_id
                """,
                tenant=tenant,
                values=scope.folder_ids,
            )
        )
    if scope.created_at is not None or scope.updated_at is not None:
        candidate_sets.append(
            _query_document_ids_for_timestamps(
                session,
                tenant=tenant,
                scope=scope,
            )
        )
    if not candidate_sets:
        return set()
    return set.intersection(*candidate_sets)


def _query_document_ids_for_timestamps(
    session: Any,
    *,
    tenant: str,
    scope: SearchScope,
) -> set[str]:
    conditions = ["d.tenant = $tenant"]
    parameters: dict[str, object] = {"tenant": tenant}
    for field_name, timestamp_range in (
        ("created_at", scope.created_at),
        ("updated_at", scope.updated_at),
    ):
        if timestamp_range is None:
            continue
        for operator_name, cypher_operator in (
            ("gt", ">"),
            ("gte", ">="),
            ("lt", "<"),
            ("lte", "<="),
        ):
            value = getattr(timestamp_range, operator_name)
            if value is None:
                continue
            parameter_name = f"{field_name}_{operator_name}"
            conditions.append(
                f"datetime(d.{field_name}) {cypher_operator} datetime(${parameter_name})"
            )
            parameters[parameter_name] = value
    records = session.run(
        f"""
        MATCH (d:Document)
        WHERE {" AND ".join(conditions)}
        RETURN DISTINCT d.document_id AS document_id
        """,
        **parameters,
    )
    return {
        document_id
        for record in records
        if (document_id := _record_text(record, "document_id"))
    }


def _query_document_ids(
    session: Any,
    cypher: str,
    *,
    tenant: str,
    values: tuple[str, ...],
) -> set[str]:
    records = session.run(cypher, tenant=tenant, values=list(values))
    return {
        document_id
        for record in records
        if (document_id := _record_text(record, "document_id"))
    }


def _relationship_confidence(value: object) -> float | None:
    if value is None:
        return 1.0
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    confidence = float(value)
    if not math.isfinite(confidence) or confidence < 0.0 or confidence > 1.0:
        return None
    return confidence


def _graph_search_queries() -> tuple[tuple[str, str], ...]:
    scoped = "AND ($document_ids = [] OR d.document_id IN $document_ids)"
    return (
        (
            f"""
            MATCH (d:Document)
            WHERE d.tenant = $tenant
              AND toLower(coalesce(d.label, '')) CONTAINS $query
              {scoped}
            RETURN d, 1.0 AS confidence
            """,
            "DOCUMENT_TITLE",
        ),
        (
            f"""
            MATCH (d:Document)-[r:HAS_SIGNAL]->(s:DocumentSignal)
            WHERE d.tenant = $tenant
              AND r.tenant = $tenant
              AND s.tenant = $tenant
              AND (
                toLower(s.text) CONTAINS $query
                OR toLower(s.signal_key) CONTAINS $query
              )
              {scoped}
            RETURN d, r.confidence AS confidence
            """,
            "HAS_SIGNAL",
        ),
        (
            f"""
            MATCH (d:Document)-[r:IN_FOLDER]->(f:Folder)
            WHERE d.tenant = $tenant
              AND r.tenant = $tenant
              AND f.tenant = $tenant
              AND (
                toLower(f.label) CONTAINS $query
                OR toLower(coalesce(f.description, '')) CONTAINS $query
              )
              AND coalesce(f.projection_state, 'reference') <> 'deleted'
              {scoped}
            RETURN d, r.confidence AS confidence
            """,
            "IN_FOLDER",
        ),
        (
            f"""
            MATCH (d:Document)-[in_folder:IN_FOLDER]->(f:Folder)
                  -[child_of:CHILD_OF*1..2]->(matched:Folder)
            WHERE d.tenant = $tenant
              AND in_folder.tenant = $tenant
              AND f.tenant = $tenant
              AND matched.tenant = $tenant
              AND all(edge IN child_of WHERE edge.tenant = $tenant)
              AND (
                toLower(matched.label) CONTAINS $query
                OR toLower(coalesce(matched.description, '')) CONTAINS $query
              )
              AND coalesce(f.projection_state, 'reference') <> 'deleted'
              AND coalesce(matched.projection_state, 'reference') <> 'deleted'
              {scoped}
            RETURN d, 1.0 AS confidence
            """,
            "FOLDER_DESCENDANT",
        ),
        (
            """
            MATCH (matched:Folder)
            WHERE matched.tenant = $tenant
              AND (
                toLower(matched.label) CONTAINS $query
                OR toLower(coalesce(matched.description, '')) CONTAINS $query
              )
              AND coalesce(matched.projection_state, 'reference') <> 'deleted'
            MATCH (matched)-[matched_child_of:CHILD_OF]->(parent:Folder)
                  <-[sibling_child_of:CHILD_OF]-(sibling:Folder)
            MATCH (d:Document)-[in_folder:IN_FOLDER]->(sibling)
            WHERE d.tenant = $tenant
              AND parent.tenant = $tenant
              AND sibling.tenant = $tenant
              AND matched_child_of.tenant = $tenant
              AND sibling_child_of.tenant = $tenant
              AND in_folder.tenant = $tenant
              AND coalesce(parent.projection_state, 'reference') <> 'deleted'
              AND coalesce(sibling.projection_state, 'reference') <> 'deleted'
              AND ($document_ids = [] OR d.document_id IN $document_ids)
            RETURN d, 1.0 AS confidence
            """,
            "FOLDER_SIBLING",
        ),
    )


def _folders_from_records(value: object) -> tuple[RetrievedFolder, ...]:
    if not isinstance(value, list | tuple):
        return ()
    folders: list[RetrievedFolder] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        tenant = _record_text(item, "tenant")
        folder_id = _record_text(item, "folder_id")
        source_version = _record_text(item, "source_version", default="")
        if not tenant or not folder_id:
            continue
        folders.append(
            RetrievedFolder(
                tenant=tenant,
                folder_id=folder_id,
                source_version=source_version,
                created_at=_record_text(item, "created_at"),
                updated_at=_record_text(item, "updated_at"),
                name=_record_text(item, "name"),
                path=_record_optional_text(item, "path_snapshot"),
                description=_record_text(item, "description"),
            )
        )
    return tuple(folders)


def _record_optional_text(item: dict[str, object], key: str) -> str | None:
    value = item.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _record_text(
    item: dict[str, object],
    key: str,
    *,
    default: str | None = None,
) -> str:
    value = item.get(key)
    if value is None:
        return default or ""
    if not isinstance(value, str):
        return ""
    stripped = value.strip()
    if stripped:
        return stripped
    return default or ""
