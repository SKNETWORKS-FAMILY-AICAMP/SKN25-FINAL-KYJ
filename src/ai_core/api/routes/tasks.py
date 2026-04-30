from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ai_core.api.errors import invalid_input_response
from ai_core.api.dto.action_results import (
    RecordHostActionResultRequest,
    RecordHostActionResultResponse,
)
from ai_core.api.dto.tasks import CreateTaskRequest, TaskSnapshotResponse
from ai_core.application.use_cases.record_action_result import RecordActionResultUseCase
from ai_core.application.use_cases.run_task import RunTaskUseCase
from ai_core.common.validation import InvalidInputError


def create_tasks_router(
    *,
    run_task: RunTaskUseCase,
    record_action_result: RecordActionResultUseCase,
) -> APIRouter:
    router = APIRouter(prefix="/tasks", tags=["tasks"])

    @router.post("", response_model=TaskSnapshotResponse)
    def create_task_endpoint(request: CreateTaskRequest) -> TaskSnapshotResponse:
        try:
            snapshot = run_task.execute(request.to_model())
        except InvalidInputError as exc:
            raise invalid_input_response(exc) from exc
        return TaskSnapshotResponse.from_model(snapshot)

    @router.post("/actions/result", response_model=RecordHostActionResultResponse)
    def record_action_result_endpoint(
        request: RecordHostActionResultRequest,
    ) -> RecordHostActionResultResponse:
        try:
            record_action_result.execute(
                tenant=request.tenant,
                task_id=request.task_id,
                result=request.to_model_result(),
            )
        except InvalidInputError as exc:
            raise invalid_input_response(exc) from exc
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return RecordHostActionResultResponse(recorded=True)

    return router
