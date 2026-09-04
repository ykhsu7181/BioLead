"""API response and error helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


@dataclass
class ApiError(Exception):
    """Structured API error."""

    code: str
    message: str
    status_code: int = 400


def api_success(data: Any, *, request_id: str | None = None) -> dict[str, Any]:
    return {
        "success": True,
        "data": data,
        "error": None,
        "request_id": request_id or _request_id(),
    }


def api_error_response(error: ApiError, *, request_id: str | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={
            "success": False,
            "data": None,
            "error": {"code": error.code, "message": error.message},
            "request_id": request_id or _request_id(),
        },
    )


async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    return api_error_response(exc)


async def request_validation_error_handler(
    _: Request,
    __: RequestValidationError,
) -> JSONResponse:
    return api_error_response(
        ApiError(
            code="INVALID_REQUEST",
            message="Request validation failed.",
            status_code=422,
        )
    )


async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    return api_error_response(
        ApiError(
            code="INTERNAL_ERROR",
            message="An unexpected server error occurred.",
            status_code=500,
        )
    )


def _request_id() -> str:
    return f"req-{uuid4()}"
