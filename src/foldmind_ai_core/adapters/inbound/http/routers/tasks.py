from __future__ import annotations

from fastapi import APIRouter

from foldmind_ai_core.adapters.inbound.http.application_errors import ApplicationErrorRoute
from foldmind_ai_core.adapters.inbound.http.dtos.actions import (
    RecordHostActionResultRequest,
)
from foldmind_ai_core.adapters.inbound.http.dtos.tasks import (
    AppendTaskInputRequest,
    CreateTaskRequest,
    RecordHostActionResultResponse,
    TaskSnapshotResponse,
)
from foldmind_ai_core.adapters.inbound.http.mappers.actions import (
    record_action_result_command_from_request,
)
from foldmind_ai_core.adapters.inbound.http.mappers.tasks import (
    append_task_command_from_request,
    create_task_command_from_request,
    get_task_query_from_path,
    record_action_result_response_from_result,
    remove_task_input_command_from_path,
    task_snapshot_response_from_result,
)
from foldmind_ai_core.core.application.ports.inbound.workflow import TaskWorkflowServicePort


def create_tasks_router(
    *,
    task_workflow: TaskWorkflowServicePort,
) -> APIRouter:
    router = APIRouter(
        prefix="/tasks",
        tags=["tasks"],
        route_class=ApplicationErrorRoute,
    )

    @router.post("", response_model=TaskSnapshotResponse)
    async def create_task_endpoint(request: CreateTaskRequest) -> TaskSnapshotResponse:
        result = await task_workflow.create_task(create_task_command_from_request(request))
        return task_snapshot_response_from_result(result)

    @router.post("/{task_id}/inputs", response_model=TaskSnapshotResponse)
    async def append_task_input_endpoint(
        task_id: str,
        request: AppendTaskInputRequest,
    ) -> TaskSnapshotResponse:
        result = await task_workflow.append_task_input(
            append_task_command_from_request(
                task_id=task_id,
                request=request,
            )
        )
        return task_snapshot_response_from_result(result)

    @router.get("/{task_id}", response_model=TaskSnapshotResponse)
    async def get_task_endpoint(task_id: str) -> TaskSnapshotResponse:
        result = await task_workflow.get_task(get_task_query_from_path(task_id=task_id))
        return task_snapshot_response_from_result(result)

    @router.delete(
        "/inputs/{task_input_id}",
        response_model=TaskSnapshotResponse,
    )
    async def remove_task_input_endpoint(
        task_input_id: str,
    ) -> TaskSnapshotResponse:
        result = await task_workflow.remove_task_input(
            remove_task_input_command_from_path(
                task_input_id=task_input_id,
            )
        )
        return task_snapshot_response_from_result(result)

    @router.post("/actions/result", response_model=RecordHostActionResultResponse)
    async def record_action_result_endpoint(
        request: RecordHostActionResultRequest,
    ) -> RecordHostActionResultResponse:
        result = await task_workflow.record_action_result(
            record_action_result_command_from_request(request)
        )
        return record_action_result_response_from_result(result)

    return router
