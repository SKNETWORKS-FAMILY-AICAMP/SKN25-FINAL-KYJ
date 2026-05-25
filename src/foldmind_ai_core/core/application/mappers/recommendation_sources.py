from __future__ import annotations

from foldmind_ai_core.core.application.models.recommendation import (
    FolderRecommendationSourceRequest,
)
from foldmind_ai_core.core.domain.models.document_sources import (
    DocumentSourceState,
    SourceDocument,
)
from foldmind_ai_core.shared.input_digest import input_digest
from foldmind_ai_core.shared.types import JsonObject, Metadata
from foldmind_ai_core.shared.validation import InvalidInputError

_MISSING = object()
_INTERNAL_DOCUMENT_ID_PREFIX = "task-document-"


def source_document_from_indexed_projection(
    *,
    source: DocumentSourceState,
    body: str,
) -> SourceDocument:
    return SourceDocument(
        tenant=source.tenant,
        document_type=source.document_type,
        document_id=source.document_id,
        source_version=source.source_version,
        title=source.title,
        body=body,
        created_at=source.created_at,
        updated_at=source.updated_at,
        metadata=dict(source.metadata),
    )


def source_document_from_explicit_request(
    request: FolderRecommendationSourceRequest,
    document_data: JsonObject,
) -> SourceDocument:
    default_body = "" if request.context_document_id is not None else request.request_text
    metadata = _metadata_value(
        _option_or_document_value("metadata", {}, document_data, request.options)
    )
    default_document_id = _default_document_id(
        request=request,
        document_data=document_data,
        body=default_body,
    )
    return SourceDocument(
        tenant=request.tenant,
        document_type=_normalized_string_value(
            _option_or_document_value(
                "document_type",
                "document",
                document_data,
                request.options,
            ),
            name="document_type",
            default="document",
        ),
        document_id=_normalized_string_value(
            _option_or_document_value(
                "document_id",
                default_document_id,
                document_data,
                request.options,
            ),
            name="document_id",
            default=default_document_id,
        ),
        source_version=_normalized_string_value(
            _option_or_document_value(
                "source_version",
                "task",
                document_data,
                request.options,
            ),
            name="source_version",
            default="task",
        ),
        title=_string_value(
            _option_or_document_value("title", "", document_data, request.options),
            name="title",
            default="",
        ),
        body=_string_value(
            _option_or_document_value("body", default_body, document_data, request.options),
            name="body",
            default=default_body,
        ),
        created_at=_normalized_string_value(
            _option_or_document_value(
                "created_at",
                request.requested_at,
                document_data,
                request.options,
            ),
            name="created_at",
            default=request.requested_at,
        ),
        updated_at=_normalized_string_value(
            _option_or_document_value(
                "updated_at",
                request.requested_at,
                document_data,
                request.options,
            ),
            name="updated_at",
            default=request.requested_at,
        ),
        metadata=metadata,
    )


def folder_ids_from_explicit_request(
    request: FolderRecommendationSourceRequest,
    document_data: JsonObject,
) -> tuple[str, ...]:
    return _string_tuple(
        _option_or_document_value("folder_ids", (), document_data, request.options),
        name="folder_ids",
    )


def document_data_from_request(request: FolderRecommendationSourceRequest) -> JsonObject:
    if request.task_document is None:
        return {}
    if not isinstance(request.task_document, dict):
        raise InvalidInputError("task document metadata must be an object.")
    return dict(request.task_document)


def has_explicit_document_text(
    document_data: JsonObject,
    options: JsonObject,
) -> bool:
    for source in (options, document_data):
        for name in ("title", "body"):
            value = source.get(name, _MISSING)
            if value is _MISSING or value is None:
                continue
            if not isinstance(value, str):
                raise InvalidInputError(f"{name} option must be a string.")
            if value.strip():
                return True
    return False


def unique_folder_ids(values: tuple[str | None, ...]) -> tuple[str, ...]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return tuple(unique)


def is_internal_request_document_id(document_id: str) -> bool:
    return document_id.startswith(_INTERNAL_DOCUMENT_ID_PREFIX)


def _option_or_document_value(
    name: str,
    default: object,
    document_data: JsonObject,
    options: JsonObject,
) -> object:
    return options.get(name, document_data.get(name, default))


def _metadata_value(value: object) -> Metadata:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    raise InvalidInputError("metadata must be a dictionary.")


def _string_value(value: object, *, name: str, default: str) -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    raise InvalidInputError(f"{name} option must be a string.")


def _normalized_string_value(value: object, *, name: str, default: str) -> str:
    normalized = _string_value(value, name=name, default=default).strip()
    return normalized or default


def _default_document_id(
    *,
    request: FolderRecommendationSourceRequest,
    document_data: JsonObject,
    body: str,
) -> str:
    if request.context_document_id is not None and request.context_document_id.strip():
        return request.context_document_id.strip()
    digest = input_digest(
        "folder-recommendation-source-document",
        {
            "tenant": request.tenant,
            "requested_at": request.requested_at,
            "request_text": request.request_text,
            "title": _option_or_document_value(
                "title",
                "",
                document_data,
                request.options,
            ),
            "body": _option_or_document_value(
                "body",
                body,
                document_data,
                request.options,
            ),
        },
    )
    return f"{_INTERNAL_DOCUMENT_ID_PREFIX}{digest[:16]}"


def _string_tuple(value: object, *, name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        stripped = value.strip()
        return (stripped,) if stripped else ()
    if isinstance(value, list | tuple):
        values: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise InvalidInputError(f"{name} must contain strings.")
            stripped = item.strip()
            if stripped:
                values.append(stripped)
        return tuple(values)
    raise InvalidInputError(f"{name} must be a string or sequence of strings.")
