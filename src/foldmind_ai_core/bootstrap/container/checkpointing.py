from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from foldmind_ai_core.adapters.outbound.workflow_runtime.checkpoint_codec import (
    langgraph_checkpoint_serializer,
)
from foldmind_ai_core.bootstrap.settings import APISettings

_WORKFLOW_CHECKPOINTER_CONTEXTS: list[Any] = []


def build_workflow_checkpointer(settings: APISettings) -> Any:
    checkpoint_dsn = settings.workflow_checkpoint_dsn or settings.postgres_dsn
    if checkpoint_dsn:
        return build_postgres_workflow_checkpointer(checkpoint_dsn)
    if settings.allow_in_memory_workflow_checkpoint:
        return InMemorySaver(serde=langgraph_checkpoint_serializer())
    raise RuntimeError(
        "Workflow checkpoint storage is required. Set "
        "FOLDMIND_WORKFLOW_CHECKPOINT_DSN or explicitly allow the in-memory "
        "workflow checkpointer for local/test use."
    )


def build_postgres_workflow_checkpointer(dsn: str) -> Any:
    from langgraph.checkpoint.postgres import PostgresSaver

    from_conn_string: Any = PostgresSaver.from_conn_string
    checkpointer_source = from_conn_string(
        dsn,
        serde=langgraph_checkpoint_serializer(),
    )
    checkpointer = checkpointer_source
    if hasattr(checkpointer_source, "__enter__") and hasattr(checkpointer_source, "__exit__"):
        checkpointer = checkpointer_source.__enter__()
        _WORKFLOW_CHECKPOINTER_CONTEXTS.append(checkpointer_source)
    return checkpointer
