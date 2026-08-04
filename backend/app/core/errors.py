import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Business error with an HTTP status and a machine-readable code."""

    def __init__(
        self,
        message: str,
        code: str = "bad_request",
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", code: str = "not_found"):
        super().__init__(message, code, status.HTTP_404_NOT_FOUND)


class PermissionError(AppError):
    def __init__(self, message: str = "Not allowed", code: str = "forbidden"):
        super().__init__(message, code, status.HTTP_403_FORBIDDEN)


class ConflictError(AppError):
    def __init__(self, message: str = "Conflict", code: str = "conflict"):
        super().__init__(message, code, status.HTTP_409_CONFLICT)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"ok": False, "code": exc.code, "message": exc.message},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError):
        errors = [
            {
                "loc": list(e.get("loc", [])),
                "msg": e.get("msg", "validation error"),
            }
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"ok": False, "code": "validation_error", "message": "Invalid input", "errors": errors},
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(_: Request, exc: Exception):
        logger.exception("unhandled error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"ok": False, "code": "internal_error", "message": "Internal server error"},
        )
