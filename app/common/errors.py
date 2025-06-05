from logging import getLogger
from typing import Optional

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.common.exceptions import (
    AppError,
    ConflictError,
    NotFoundError,
    ValidationError,
)

logger = getLogger(__name__)


class ErrorResponse:
    """Standardized error response model."""

    def __init__(self, error_message: str, code: Optional[str] = None):
        self.status = "ERROR"
        self.error_message = error_message
        self.code = code

    def to_dict(self):
        result = {"status": self.status, "error_message": self.error_message}
        if self.code:
            result["code"] = self.code
        return result


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware to handle exceptions and return standardized error responses."""

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except AppError as e:
            logger.warning("Application error: %s", e.message, exc_info=True)
            status_code = self._get_status_code(e)
            error_response = ErrorResponse(e.message, e.code)
            return JSONResponse(
                status_code=status_code, content=error_response.to_dict()
            )
        except HTTPException as e:
            # Let FastAPI handle HTTP exceptions
            raise e
        except Exception as e:
            logger.exception("Unexpected error: %s", str(e))
            error_response = ErrorResponse("Internal server error")
            return JSONResponse(status_code=500, content=error_response.to_dict())

    def _get_status_code(self, exception: AppError) -> int:
        """Map exception types to HTTP status codes."""
        if isinstance(exception, NotFoundError):
            return 404
        if isinstance(exception, ValidationError):
            return 400
        if isinstance(exception, ConflictError):
            return 409
        return 500
