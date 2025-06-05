from typing import Optional


class AppError(Exception):
    """Base exception for application errors."""

    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(AppError):
    """Raised when a resource is not found."""


class ValidationError(AppError):
    """Raised when validation fails."""


class ConflictError(AppError):
    """Raised when there is a conflict with the current state."""


class UnsupportedFileTypeError(ValidationError):
    """Raised when an unsupported file type is uploaded."""

    def __init__(self, message: str = "Unsupported file type"):
        super().__init__(message, "UNSUPPORTED_FILE_TYPE")


class InvalidStatusError(ValidationError):
    """Raised when an invalid status transition is attempted."""

    def __init__(self, message: str = "Invalid status"):
        super().__init__(message, "INVALID_STATUS")
