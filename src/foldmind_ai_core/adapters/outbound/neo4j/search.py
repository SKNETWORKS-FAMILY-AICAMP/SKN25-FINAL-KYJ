from __future__ import annotations

from typing import Any

from foldmind_ai_core.adapters.outbound.neo4j.mappers import (
    document_from_node,
    matches_scope,
)
from foldmind_ai_core.domain.retrieval.queries import SearchScope
from foldmind_ai_core.domain.retrieval.results import (
    DocumentRetrievalResult,
    RetrievedDocument,
    RetrievedFolder,
)

_SIGNAL_WEIGHTS = {
    "ABOUT": 0.75,
    "HAS_TAG": 0.90,
    "TAG_REPRESENTS": 0.60,
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
    if _requires_relationship_scope(scope) and not scoped_document_ids:
        return []

    scores: dict[tuple[str, str, str], float] = {}
    documents: dict[tuple[str, str, str], RetrievedDocument] = {}
    for cypher, signal_type in _graph_search_queries():
        records = session.run(
            cypher,
            tenant=tenant,
            query=query,
            document_ids=list(scoped_document_ids),
        )
        for record in records:
            document = document_from_node(record["d"])
            if not document.document_id.strip():
                continue
            if not matches_scope(document, scope):
                continue
            if scoped_document_ids and document.document_id not in scoped_document_ids:
                continue
            key = (document.tenant, document.document_type, document.document_id)
            confidence = float(record.get("confidence", 1.0) or 1.0)
            scores[key] = scores.get(key, 0.0) + (
                _SIGNAL_WEIGHTS[signal_type] * confidence
            )
            documents[key] = document
    ranked = [
        DocumentRetrievalResult(document=documents[key], score=score)
        for key, score in scores.items()
    ]
    ranked.sort(key=lambda result: result.score, reverse=True)
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
        MATCH (d:Document {tenant: $tenant})-[:IN_FOLDER]->(f:Folder {tenant: $tenant})
        WHERE d.document_id IN $document_ids
          AND coalesce(f.deleted, false) = false
        RETURN d.document_id AS document_id,
               collect(DISTINCT {
                   tenant: f.tenant,
                   folder_id: f.folder_id,
                   source_version: f.source_version
               }) AS folders
        """,
        tenant=tenant,
        document_ids=list(document_ids),
    )
    folders_by_document: dict[str, tuple[RetrievedFolder, ...]] = {}
    for record in records:
        document_id = str(record["document_id"]).strip()
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
    explicit_ids = _explicit_document_ids(scope)
    if explicit_ids:
        candidate_sets.append(explicit_ids)
    if scope.folder_ids:
        candidate_sets.append(
            _query_document_ids(
                session,
                """
                MATCH (d:Document {tenant: $tenant})-[:IN_FOLDER]->(f:Folder {tenant: $tenant})
                WHERE f.folder_id IN $values
                  AND coalesce(f.deleted, false) = false
                RETURN DISTINCT d.document_id AS document_id
                """,
                tenant=tenant,
                values=scope.folder_ids,
            )
        )
    if scope.tag_ids:
        candidate_sets.append(
            _query_document_ids(
                session,
                """
                MATCH (d:Document {tenant: $tenant})-[:HAS_TAG]->(t:Tag {tenant: $tenant})
                WHERE t.tag_id IN $values
                RETURN DISTINCT d.document_id AS document_id
                """,
                tenant=tenant,
                values=scope.tag_ids,
            )
        )
    if not candidate_sets:
        return set()
    return _intersect_all(candidate_sets)


def _explicit_document_ids(scope: SearchScope) -> set[str]:
    document_ids = set(scope.document_ids)
    if scope.document_id is not None:
        document_ids.add(scope.document_id)
    return document_ids


def _intersect_all(candidate_sets: list[set[str]]) -> set[str]:
    scoped = candidate_sets[0]
    for candidate_set in candidate_sets[1:]:
        scoped = scoped.intersection(candidate_set)
    return scoped


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
        if (document_id := str(record["document_id"]).strip())
    }


def _requires_relationship_scope(scope: SearchScope | None) -> bool:
    return bool(scope is not None and (scope.folder_ids or scope.tag_ids))


def _graph_search_queries() -> tuple[tuple[str, str], ...]:
    scoped = "AND ($document_ids = [] OR d.document_id IN $document_ids)"
    return (
        (
            f"""
            MATCH (d:Document {{tenant: $tenant}})-[r:ABOUT]->(c:Concept {{tenant: $tenant}})
            WHERE toLower(c.label) CONTAINS $query
              {scoped}
            RETURN d, r.confidence AS confidence
            """,
            "ABOUT",
        ),
        (
            f"""
            MATCH (d:Document {{tenant: $tenant}})-[r:HAS_TAG]->(t:Tag {{tenant: $tenant}})
            WHERE (toLower(t.label) CONTAINS $query
               OR toLower(t.normalized_label) CONTAINS $query)
              {scoped}
            RETURN d, r.confidence AS confidence
            """,
            "HAS_TAG",
        ),
        (
            f"""
            MATCH (d:Document {{tenant: $tenant}})-[r:IN_FOLDER]->(f:Folder {{tenant: $tenant}})
            WHERE toLower(f.label) CONTAINS $query
              AND coalesce(f.deleted, false) = false
              {scoped}
            RETURN d, r.confidence AS confidence
            """,
            "IN_FOLDER",
        ),
        (
            f"""
            MATCH (d:Document {{tenant: $tenant}})-[:IN_FOLDER]->(f:Folder {{tenant: $tenant}})
                  -[:CHILD_OF*1..2]->(matched:Folder {{tenant: $tenant}})
            WHERE toLower(matched.label) CONTAINS $query
              AND coalesce(f.deleted, false) = false
              AND coalesce(matched.deleted, false) = false
              {scoped}
            RETURN d, 1.0 AS confidence
            """,
            "FOLDER_DESCENDANT",
        ),
        (
            """
            MATCH (matched:Folder {tenant: $tenant})
            WHERE toLower(matched.label) CONTAINS $query
              AND coalesce(matched.deleted, false) = false
            MATCH (matched)-[:CHILD_OF]->(parent:Folder)<-[:CHILD_OF]-(sibling:Folder)
            MATCH (d:Document {tenant: $tenant})-[:IN_FOLDER]->(sibling)
            WHERE coalesce(parent.deleted, false) = false
              AND coalesce(sibling.deleted, false) = false
              AND ($document_ids = [] OR d.document_id IN $document_ids)
            RETURN d, 1.0 AS confidence
            """,
            "FOLDER_SIBLING",
        ),
        (
            """
            MATCH (t:Tag {tenant: $tenant})-[:REPRESENTS]->(c:Concept {tenant: $tenant})
            WHERE toLower(c.label) CONTAINS $query
            MATCH (d:Document {tenant: $tenant})-[r:HAS_TAG]->(t)
            WHERE ($document_ids = [] OR d.document_id IN $document_ids)
            RETURN d, r.confidence AS confidence
            """,
            "TAG_REPRESENTS",
        ),
    )


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(str(item) for item in value if item is not None and str(item).strip())


def _folders_from_records(value: object) -> tuple[RetrievedFolder, ...]:
    if not isinstance(value, list | tuple):
        return ()
    folders: list[RetrievedFolder] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        folder_id = str(item.get("folder_id") or "").strip()
        source_version = str(item.get("source_version") or "").strip()
        if not folder_id or not source_version:
            continue
        folders.append(
            RetrievedFolder(
                tenant=str(item.get("tenant") or ""),
                folder_id=folder_id,
                source_version=source_version,
            )
        )
    return tuple(folders)
