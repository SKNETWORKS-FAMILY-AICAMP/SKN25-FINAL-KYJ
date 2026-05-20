from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.core.application.errors import ResourceNotFoundError
from foldmind_ai_core.core.application.ports.outbound.graph_store import GraphStore
from foldmind_ai_core.core.application.ports.outbound.indexed_document_source import (
    IndexedDocumentSourceRepository,
)
from foldmind_ai_core.core.domain.models.reference.documents import SourceDocument
from foldmind_ai_core.shared.types import JsonObject, JsonValue, Metadata

_MISSING = object()


@dataclass(frozen=True, slots=True)
class FolderRecommendationSourceRequest:
    tenant: str
    request_text: str
    requested_at: str
    context_document_id: str | None = None
    context_folder_id: str | None = None
    task_document: JsonValue = None
    options: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FolderRecommendationSource:
    document: SourceDocument
    folder_ids: tuple[str, ...] = ()


@dataclass(slots=True)
class FolderRecommendationSourceResolver:
    indexed_documents: IndexedDocumentSourceRepository
    graph: GraphStore

    def resolve(self, request: FolderRecommendationSourceRequest) -> FolderRecommendationSource:
        document_data = _document_metadata(request.task_document)
        if _has_explicit_document_text(document_data, request.options):
            return self._with_current_folder_exclusions(
                _source_from_explicit_document(request, document_data),
                request,
                explicit_folder_ids=_folder_ids_from_document_data(
                    request,
                    document_data,
                ),
            )
        if request.context_document_id is not None:
            source = self.indexed_documents.get_current_document_source(
                tenant=request.tenant,
                document_id=request.context_document_id,
            )
            if source is None:
                raise ResourceNotFoundError(
                    "Current indexed document source not found: "
                    f"{request.context_document_id}"
                )
            return self._with_current_folder_exclusions(source, request)
        return self._with_current_folder_exclusions(
            _source_from_explicit_document(request, document_data),
            request,
            explicit_folder_ids=_folder_ids_from_document_data(request, document_data),
        )

    def _with_current_folder_exclusions(
        self,
        source: SourceDocument,
        request: FolderRecommendationSourceRequest,
        explicit_folder_ids: tuple[str, ...] = (),
    ) -> FolderRecommendationSource:
        graph_folder_ids: tuple[str, ...] = ()
        if source.document_id:
            folders_by_document = self.graph.folders_for_documents(
                tenant=source.tenant,
                document_ids=(source.document_id,),
            )
            graph_folder_ids = tuple(
                folder.folder_id
                for folder in folders_by_document.get(source.document_id, ())
                    if folder.folder_id.strip()
            )

        base_folder_ids = graph_folder_ids
        if not base_folder_ids and request.context_document_id is not None:
            base_folder_ids = self.indexed_documents.get_current_document_folder_ids(
                tenant=request.tenant,
                document_id=request.context_document_id,
            )
        if not base_folder_ids:
            base_folder_ids = explicit_folder_ids
        folder_ids = _unique_strings(
            (
                *base_folder_ids,
                *(
                    (request.context_folder_id,)
                    if request.context_folder_id is not None
                    else ()
                ),
            )
        )
        return FolderRecommendationSource(document=source, folder_ids=folder_ids)


def _source_from_explicit_document(
    request: FolderRecommendationSourceRequest,
    document_data: JsonObject,
) -> SourceDocument:
    default_document_id = request.context_document_id or ""
    default_body = "" if request.context_document_id is not None else request.request_text
    metadata_value = _option_or_document_value(
        "metadata",
        {},
        document_data,
        request.options,
    )
    metadata = _metadata_value(metadata_value)
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


def _folder_ids_from_document_data(
    request: FolderRecommendationSourceRequest,
    document_data: JsonObject,
) -> tuple[str, ...]:
    return _string_tuple(
        _option_or_document_value("folder_ids", (), document_data, request.options),
        name="folder_ids",
    )


def _document_metadata(value: JsonValue) -> JsonObject:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError("task document metadata must be an object.")
    return dict(value)


def _has_explicit_document_text(
    document_data: JsonObject,
    options: JsonObject,
) -> bool:
    for source in (options, document_data):
        for name in ("title", "body"):
            value = source.get(name, _MISSING)
            if value is _MISSING or value is None:
                continue
            if not isinstance(value, str):
                raise TypeError(f"{name} option must be a string.")
            if value.strip():
                return True
    return False


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
    raise TypeError("metadata must be a dictionary.")


def _string_value(value: object, *, name: str, default: str) -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    raise TypeError(f"{name} option must be a string.")


def _normalized_string_value(value: object, *, name: str, default: str) -> str:
    normalized = _string_value(value, name=name, default=default).strip()
    return normalized or default


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
                raise TypeError(f"{name} must contain strings.")
            stripped = item.strip()
            if stripped:
                values.append(stripped)
        return tuple(values)
    raise TypeError(f"{name} must be a string or sequence of strings.")


def _unique_strings(values: tuple[str | None, ...]) -> tuple[str, ...]:
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
