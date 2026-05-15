from __future__ import annotations

from fastapi import HTTPException

from foldmind_ai_core.shared.validation import InvalidInputError


def invalid_input_response(exc: InvalidInputError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))
