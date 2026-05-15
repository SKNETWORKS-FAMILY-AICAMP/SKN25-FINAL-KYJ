from __future__ import annotations

from fastapi import APIRouter, HTTPException

from foldmind_ai_core.adapters.inbound.http.error_handlers import invalid_input_response
from foldmind_ai_core.adapters.inbound.http.schemas.actions import (
    RecordHostActionResultRequest,
)
from foldmind_ai_core.adapters.inbound.http.schemas.tasks import (
    AppendTaskRequest,
    CreateTaskRequest,
    RecordHostActionResultResponse,
    TaskSnapshotResponse,
)
from foldmind_ai_core.application.errors import ResourceNotFoundError
from foldmind_ai_core.application.ports.inbound.workflow_use_case import (
    GetTaskUseCasePort,
    RecordActionResultUseCasePort,
    RemoveTaskRequestUseCasePort,
    RunTaskUseCasePort,
)
from foldmind_ai_core.shared.validation import InvalidInputError


def create_tasks_router(
    *,
    run_task: RunTaskUseCasePort,
    get_task: GetTaskUseCasePort,
    remove_task_request: RemoveTaskRequestUseCasePort,
    record_action_result: RecordActionResultUseCasePort,
) -> APIRouter:
    router = APIRouter(prefix="/tasks", tags=["tasks"])

    @router.post("", response_model=TaskSnapshotResponse)
    def create_task_endpoint(request: CreateTaskRequest) -> TaskSnapshotResponse:
        try:
            snapshot = run_task.execute(request.to_model())
        except InvalidInputError as exc:
            raise invalid_input_response(exc) from exc
        return TaskSnapshotResponse.from_model(snapshot)

    @router.post("/{task_id}/requests", response_model=TaskSnapshotResponse)
    def append_task_request_endpoint(
        task_id: str,
        request: AppendTaskRequest,
    ) -> TaskSnapshotResponse:
        try:
            snapshot = run_task.execute(request.to_model(task_id=task_id))
        except InvalidInputError as exc:
            raise invalid_input_response(exc) from exc
        return TaskSnapshotResponse.from_model(snapshot)

    @router.get("/{task_id}", response_model=TaskSnapshotResponse)
    def get_task_endpoint(task_id: str) -> TaskSnapshotResponse:
        try:
            snapshot = get_task.execute(task_id=task_id)
        except InvalidInputError as exc:
            raise invalid_input_response(exc) from exc
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return TaskSnapshotResponse.from_model(snapshot)

    @router.delete(
        "/requests/{task_request_id}",
        response_model=TaskSnapshotResponse,
    )
    def remove_task_request_endpoint(
        task_request_id: str,
    ) -> TaskSnapshotResponse:
        try:
            snapshot = remove_task_request.execute(
                task_request_id=task_request_id,
            )
        except InvalidInputError as exc:
            raise invalid_input_response(exc) from exc
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return TaskSnapshotResponse.from_model(snapshot)

    @router.post("/actions/result", response_model=RecordHostActionResultResponse)
    def record_action_result_endpoint(
        request: RecordHostActionResultRequest,
    ) -> RecordHostActionResultResponse:
        try:
            snapshot = record_action_result.execute(
                result=request.to_model_result(),
            )
        except InvalidInputError as exc:
            raise invalid_input_response(exc) from exc
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return RecordHostActionResultResponse(
            recorded=True,
            task=TaskSnapshotResponse.from_model(snapshot).task,
        )

    return router
