from __future__ import annotations

from foldmind_ai_core.core.application.workflows import option_values
from foldmind_ai_core.core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.core.domain.models.reference.documents import SourceDocument
from foldmind_ai_core.core.application.queries.retrieval import RetrievalQuery
from foldmind_ai_core.core.domain.models.workflow.actions import HostActionType
from foldmind_ai_core.shared.types import JsonObject

_MISSING = object()


def requested_host_actions(options: JsonObject) -> tuple[HostActionType, ...]:
    value = options.get("host_actions", _MISSING)
    if value is _MISSING:
        return ()

    action_types: list[HostActionType] = []
    for action_type in option_values.non_blank_string_tuple(
        value,
        name="host_actions option",
    ):
        try:
            action_types.append(HostActionType(action_type))
        except ValueError as exc:
            raise ValueError(f"Unsupported host action: {action_type}") from exc
    return tuple(action_types)


def document_from_task(
    state: WorkflowState,
    query: RetrievalQuery,
    options: JsonObject,
) -> SourceDocument:
    document_data = state.task.metadata.get("document")
    if document_data is None:
        document_data = {}
    elif not isinstance(document_data, dict):
        raise TypeError("task document metadata must be an object.")

    def option_or_document_value(name: str, default: object) -> object:
        return options.get(name, document_data.get(name, default))

    metadata_value = option_or_document_value("metadata", {})
    if metadata_value is None:
        metadata = {}
    elif isinstance(metadata_value, dict):
        metadata = dict(metadata_value)
    else:
        raise TypeError("metadata must be a dictionary.")

    return SourceDocument(
        tenant=state.task.tenant,
        document_type=option_values.normalized_string_value(
            option_or_document_value("document_type", "document"),
            name="document_type",
            default="document",
        ),
        document_id=option_values.normalized_string_value(
            option_or_document_value("document_id", ""),
            name="document_id",
            default="",
        ),
        source_version=option_values.normalized_string_value(
            options.get("source_version", document_data.get("source_version", "task")),
            name="source_version",
            default="task",
        ),
        title=option_values.string_value(
            option_or_document_value("title", ""),
            name="title",
            default="",
        ),
        body=option_values.string_value(
            option_or_document_value("body", query.text),
            name="body",
            default=query.text,
        ),
        created_at=option_values.normalized_string_value(
            option_or_document_value("created_at", query.request_context.requested_at),
            name="created_at",
            default=query.request_context.requested_at,
        ),
        updated_at=option_values.normalized_string_value(
            option_or_document_value("updated_at", query.request_context.requested_at),
            name="updated_at",
            default=query.request_context.requested_at,
        ),
        metadata=metadata,
    )
