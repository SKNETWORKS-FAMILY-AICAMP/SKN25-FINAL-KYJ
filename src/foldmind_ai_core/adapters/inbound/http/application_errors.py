from __future__ import annotations

from collections.abc import Callable, Coroutine

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from foldmind_ai_core.core.application.errors import (
    ConcurrentTaskUpdateError,
    ResourceNotFoundError,
)
from foldmind_ai_core.shared.validation import InvalidInputError


class ApplicationErrorRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[object, object, Response]]:
        original_route = super().get_route_handler()

        async def route_with_application_errors(request: Request) -> Response:
            try:
                return await original_route(request)
            except InvalidInputError as exc:
                return _invalid_input_error_response(exc)
            except ResourceNotFoundError as exc:
                return _not_found_error_response(exc)
            except ConcurrentTaskUpdateError as exc:
                return _conflict_error_response(exc)

        return route_with_application_errors


def _invalid_input_error_response(
    exc: InvalidInputError,
) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


def _not_found_error_response(
    exc: ResourceNotFoundError,
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


def _conflict_error_response(
    exc: ConcurrentTaskUpdateError,
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})
