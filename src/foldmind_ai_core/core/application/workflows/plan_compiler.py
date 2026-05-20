from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import cast

from foldmind_ai_core.core.application.queries.retrieval import (
    RetrievalQuery,
    SearchScope,
    SearchSort,
    TimestampRange,
)
from foldmind_ai_core.core.application.workflows.state.execution import (
    WorkflowExecutionPlan,
    WorkflowStep,
    WorkflowStepInput,
)
from foldmind_ai_core.core.application.workflows.state.plan import (
    WorkflowAction,
    WorkflowActionType,
    WorkflowPlan,
)
from foldmind_ai_core.shared.types import JsonObject


@dataclass(slots=True)
class WorkflowPlanCompiler:
    def compile(
        self,
        workflow_plan: WorkflowPlan,
        *,
        query: RetrievalQuery | None = None,
    ) -> WorkflowExecutionPlan:
        source_scoped_query = _query_with_source_scope(query, workflow_plan)
        if source_scoped_query is None and workflow_plan.source_scope in {
            "current_document",
            "current_folder",
        }:
            return WorkflowExecutionPlan(
                steps=[
                    WorkflowStep(
                        action_type=WorkflowActionType.REQUEST_CLARIFICATION,
                        reason="The requested current source is missing from task context.",
                        step_input=WorkflowStepInput(
                            query=query,
                            options=_missing_source_scope_options(workflow_plan.source_scope),
                        ),
                    )
                ]
            )

        steps: list[WorkflowStep] = []
        for action in _ensure_document_search_output(workflow_plan.actions):
            options = cast(JsonObject, dict(action.params))
            if action.action_type == WorkflowActionType.PLAN_HOST_ACTIONS and (
                action.requires_confirmation or workflow_plan.requires_confirmation
            ):
                options["requires_confirmation"] = True
            step_query = _query_with_temporal_scope(source_scoped_query, options)
            steps.append(
                WorkflowStep(
                    action_type=action.action_type,
                    reason=action.reason,
                    step_input=WorkflowStepInput(query=step_query, options=options),
                )
            )
        return WorkflowExecutionPlan(steps=steps)


_DOCUMENT_SEARCH_OUTPUT_ACTIONS = {
    WorkflowActionType.PRESENT_DOCUMENTS,
    WorkflowActionType.ANSWER_QUESTION,
    WorkflowActionType.SUMMARIZE_DOCUMENTS,
    WorkflowActionType.GENERATE_DRAFT,
    WorkflowActionType.EXPLORE_IDEAS,
    WorkflowActionType.RECOMMEND_DOCUMENTS,
    WorkflowActionType.SYNTHESIZE_REPORT,
    WorkflowActionType.PLAN_HOST_ACTIONS,
}

_SIGNAL_SEARCH_OUTPUT_ACTIONS = {
    WorkflowActionType.PRESENT_SIGNALS,
    WorkflowActionType.EXPAND_SIGNAL_EVIDENCE,
    WorkflowActionType.SYNTHESIZE_SIGNALS,
}


def _query_with_source_scope(
    query: RetrievalQuery | None,
    workflow_plan: WorkflowPlan,
) -> RetrievalQuery | None:
    if query is None or workflow_plan.source_scope is None:
        return query
    match workflow_plan.source_scope:
        case "current_document":
            if query.request_context.document_id is None:
                return None
            scope = _merge_source_scope(
                query.scope,
                document_id=query.request_context.document_id,
            )
        case "current_folder":
            if query.request_context.folder_id is None:
                return None
            scope = _merge_source_scope(
                query.scope,
                folder_id=query.request_context.folder_id,
            )
        case _:
            return query
    return RetrievalQuery(
        text=query.text,
        request_context=query.request_context,
        scope=scope,
        anchor=query.anchor,
    )


def _merge_source_scope(
    existing: SearchScope | None,
    *,
    document_id: str | None = None,
    folder_id: str | None = None,
) -> SearchScope:
    base_scope = existing or SearchScope()
    if document_id is not None:
        return SearchScope(
            document_type=base_scope.document_type,
            document_id=document_id,
            created_at=base_scope.created_at,
            updated_at=base_scope.updated_at,
            sort=base_scope.sort,
            metadata_filter=dict(base_scope.metadata_filter),
        )
    if folder_id is not None:
        return SearchScope(
            document_type=base_scope.document_type,
            folder_ids=(folder_id,),
            created_at=base_scope.created_at,
            updated_at=base_scope.updated_at,
            sort=base_scope.sort,
            metadata_filter=dict(base_scope.metadata_filter),
        )
    return SearchScope(
        document_type=base_scope.document_type,
        document_id=base_scope.document_id,
        document_ids=base_scope.document_ids,
        folder_ids=base_scope.folder_ids,
        created_at=base_scope.created_at,
        updated_at=base_scope.updated_at,
        sort=base_scope.sort,
        metadata_filter=dict(base_scope.metadata_filter),
    )


def _missing_source_scope_options(source_scope: str | None) -> JsonObject:
    if source_scope == "current_folder":
        return {
            "question": "어떤 폴더를 말하는지 알려주세요.",
            "reason": "요청을 처리하려면 현재 폴더 ID가 필요합니다.",
        }
    return {
        "question": "어떤 문서를 말하는지 알려주세요.",
        "reason": "요청을 처리하려면 현재 문서 ID가 필요합니다.",
    }


def _ensure_document_search_output(actions: list[WorkflowAction]) -> list[WorkflowAction]:
    action_types = {action.action_type for action in actions}
    if (
        WorkflowActionType.FIND_SIGNALS in action_types
        and not action_types & _SIGNAL_SEARCH_OUTPUT_ACTIONS
    ):
        return [
            *actions,
            WorkflowAction(
                action_type=WorkflowActionType.PRESENT_SIGNALS,
                reason="Present retrieved signals.",
            ),
        ]
    if WorkflowActionType.FIND_DOCUMENTS not in action_types:
        return actions
    if action_types & _DOCUMENT_SEARCH_OUTPUT_ACTIONS:
        return actions
    return [
        *actions,
        WorkflowAction(
            action_type=WorkflowActionType.PRESENT_DOCUMENTS,
            reason="Present retrieved documents as search results.",
        ),
    ]


def _query_with_temporal_scope(
    query: RetrievalQuery | None,
    options: JsonObject,
) -> RetrievalQuery | None:
    if query is None:
        return None
    raw_temporal = options.get("temporal")
    if raw_temporal is None:
        return query
    if not isinstance(raw_temporal, dict):
        raise ValueError("temporal params must be a JSON object.")
    scope = _merge_temporal_scope(query.scope, cast(JsonObject, raw_temporal), query)
    return RetrievalQuery(
        text=query.text,
        request_context=query.request_context,
        scope=scope,
        anchor=query.anchor,
    )


def _merge_temporal_scope(
    existing: SearchScope | None,
    temporal: JsonObject,
    query: RetrievalQuery,
) -> SearchScope:
    field = _temporal_field(temporal.get("field"))
    period_range = _period_range(temporal.get("period"), query.request_context.requested_at)
    explicit_range = _explicit_range(temporal.get("range"))
    timestamp_range = explicit_range or period_range
    base_scope = existing or SearchScope()
    sort = _temporal_sort(field=field, value=temporal.get("sort"))
    return SearchScope(
        document_type=base_scope.document_type,
        document_id=base_scope.document_id,
        document_ids=base_scope.document_ids,
        folder_ids=base_scope.folder_ids,
        created_at=(
            timestamp_range
            if field == "created_at"
            else base_scope.created_at
        ),
        updated_at=(
            timestamp_range
            if field == "updated_at"
            else base_scope.updated_at
        ),
        sort=sort or base_scope.sort,
        metadata_filter=dict(base_scope.metadata_filter),
    )


def _temporal_field(value: object) -> str:
    if value not in {"created_at", "updated_at"}:
        raise ValueError("temporal.field must be created_at or updated_at.")
    return cast(str, value)


def _temporal_sort(*, field: str, value: object) -> SearchSort | None:
    if value is None:
        return None
    if value not in {"asc", "desc"}:
        raise ValueError("temporal.sort must be asc or desc.")
    return SearchSort(field=field, direction=cast(str, value))


def _explicit_range(value: object) -> TimestampRange | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("temporal.range must be a JSON object.")
    return TimestampRange(
        gt=_optional_range_value(value.get("gt"), "temporal.range.gt"),
        gte=_optional_range_value(value.get("gte"), "temporal.range.gte"),
        lt=_optional_range_value(value.get("lt"), "temporal.range.lt"),
        lte=_optional_range_value(value.get("lte"), "temporal.range.lte"),
    )


def _optional_range_value(value: object, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string.")
    return value.strip()


def _period_range(value: object, requested_at: str) -> TimestampRange | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("temporal.period must be a string.")
    current = datetime.fromisoformat(requested_at)
    start: datetime
    end: datetime
    match value:
        case "today":
            start = current.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        case "yesterday":
            end = current.replace(hour=0, minute=0, second=0, microsecond=0)
            start = end - timedelta(days=1)
        case "this_week":
            start = _week_start(current)
            end = start + timedelta(days=7)
        case "last_week":
            end = _week_start(current)
            start = end - timedelta(days=7)
        case "this_month":
            start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = _next_month(start)
        case "last_month":
            end = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            start = _previous_month(end)
        case _:
            raise ValueError(f"Unsupported temporal.period: {value}.")
    return TimestampRange(gte=start.isoformat(), lt=end.isoformat())


def _week_start(value: datetime) -> datetime:
    day_start = value.replace(hour=0, minute=0, second=0, microsecond=0)
    return day_start - timedelta(days=day_start.weekday())


def _next_month(value: datetime) -> datetime:
    if value.month == 12:
        return value.replace(year=value.year + 1, month=1)
    return value.replace(month=value.month + 1)


def _previous_month(value: datetime) -> datetime:
    if value.month == 1:
        return value.replace(year=value.year - 1, month=12)
    return value.replace(month=value.month - 1)
