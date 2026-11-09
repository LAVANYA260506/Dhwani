"""
Application exceptions and handlers.

Every error the API returns has the same shape:

    {"error": {"code": "not_found", "message": "...", "details": ...}}

Services raise the AppError subclasses below; the handlers registered by
`register_exception_handlers(app)` turn them (and FastAPI's own validation
and HTTP errors) into that format.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("dhwani")


# ---------------------------------------------------------------------
# Exceptions raised by services and routes
# ---------------------------------------------------------------------
class AppError(Exception):
    status_code = 500
    code = "internal_error"
    default_message = "Something went wrong."

    def __init__(self, message: str | None = None, details: Any = None):
        self.message = message or self.default_message
        self.details = details
        super().__init__(self.message)


class BadRequestError(AppError):
    status_code = 400
    code = "bad_request"
    default_message = "The request could not be understood."


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"
    default_message = "A valid session is required."


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"
    default_message = "You do not have access to this application."


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    default_message = "The requested item was not found."


class ConflictError(AppError):
    """The request clashes with the current state, e.g. editing a submitted application."""

    status_code = 409
    code = "conflict"
    default_message = "This action is not allowed in the current state."


class FileTooLargeError(AppError):
    status_code = 413
    code = "file_too_large"
    default_message = "The file is too large."


class UnsupportedFileTypeError(AppError):
    status_code = 415
    code = "unsupported_file_type"
    default_message = "This file type is not supported."


class ValidationFailedError(AppError):
    status_code = 422
    code = "validation_failed"
    default_message = "Some values are not valid."


class ExternalServiceError(AppError):
    """Gnani, LlamaParse or the LLM failed or timed out."""

    status_code = 502
    code = "external_service_error"
    default_message = "A required service is not responding. Please try again."


# ---------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------
def _error_response(
    status_code: int, code: str, message: str, details: Any = None
) -> JSONResponse:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body)


async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    return _error_response(exc.status_code, exc.code, exc.message, exc.details)


async def _handle_request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {
            "field": ".".join(str(part) for part in err["loc"] if part != "body"),
            "message": err["msg"],
        }
        for err in exc.errors()
    ]
    return _error_response(
        422, "invalid_request", "The request has missing or invalid data.", details
    )


async def _handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
    return _error_response(exc.status_code, code, str(exc.detail))


async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
    # Log the real error; never show internals to the client
    logger.exception("Unhandled error", exc_info=exc)
    return _error_response(500, "internal_error", AppError.default_message)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_request_validation)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(Exception, _handle_unexpected)