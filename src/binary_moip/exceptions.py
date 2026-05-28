"""Shared exceptions for Binary MoIP clients."""


class MoIPError(Exception):
    """Base exception for all Binary MoIP errors."""


class ConnectionError(MoIPError):
    """Raised when a TCP or HTTP connection fails."""


class AuthError(MoIPError):
    """Raised when authentication fails."""


class CommandError(MoIPError):
    """Raised when a TCP control command returns an error response."""

    def __init__(self, message: str, *, response: str | None = None) -> None:
        super().__init__(message)
        self.response = response


class ApiError(MoIPError):
    """Raised when a REST API call fails."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body
