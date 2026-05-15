from __future__ import annotations

from foldmind_ai_core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.domain.reference.documents import SourceDocument
from foldmind_ai_core.domain.retrieval.queries import AIQuery
from foldmind_ai_core.domain.workflow.actions import HostActionType
from foldmind_ai_core.shared.types import Metadata


def requested_host_actions(options: Metadata) -> tuple[HostActionType, ...]:
    value = options.get("host_actions")
    raw_values: tuple[object, ...]
    if isinstance(value, str):
        raw_values = (value,)
    elif isinstance(value, list):
        raw_values = tuple(value)
    else:
        raw_values = ()

    action_types: list[HostActionType] = []
    for raw_value in raw_values:
        if not isinstance(raw_value, str):
            continue
        try:
            action_types.append(HostActionType(raw_value))
        except ValueError:
            continue
    return tuple(action_types)


def bool_option(options: Metadata, name: str) -> bool:
    return bool(options.get(name, False))


def document_from_task(
    state: WorkflowState,
    query: AIQuery,
    options: Metadata,
) -> SourceDocument:
    document_data = state.task.metadata.get("document", {})
    document_data = document_data if isinstance(document_data, dict) else {}

    def option_or_document_value(name: str, default: object) -> object:
        return options.get(name, document_data.get(name, default))

    return SourceDocument(
        tenant=state.task.tenant,
        document_type=str(option_or_document_value("document_type", "document")),
        document_id=str(option_or_document_value("document_id", "")),
        source_version=str(
            options.get("source_version", document_data.get("source_version", "task"))
        ),
        title=str(option_or_document_value("title", "")),
        body=str(option_or_document_value("body", query.text)),
        folder_ids=string_tuple(option_or_document_value("folder_ids", ())),
        tag_ids=string_tuple(
            options.get("tag_ids", document_data.get("tag_ids", ()))
        ),
        metadata=metadata_from_options(option_or_document_value("metadata", {})),
    )


def string_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value.strip() else ()
    if isinstance(value, list | tuple):
        return tuple(str(item) for item in value if str(item).strip())
    raise TypeError("Expected a string or sequence of strings.")


def metadata_from_options(value: object) -> Metadata:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError("metadata must be a dictionary.")
    return dict(value)
