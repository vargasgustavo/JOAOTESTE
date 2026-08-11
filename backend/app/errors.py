"""Erros de aplicacao com resposta JSON padronizada (sem vazar detalhes internos)."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    status_code = 400
    error_code = "bad_request"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"error": self.error_code, "message": self.message}
        if self.details is not None:
            payload["details"] = self.details
        return payload


class ValidationError(AppError):
    status_code = 422
    error_code = "validation_error"


class AuthenticationError(AppError):
    status_code = 401
    error_code = "unauthorized"


class AuthorizationError(AppError):
    status_code = 403
    error_code = "forbidden"


class NotFoundError(AppError):
    status_code = 404
    error_code = "not_found"


class ConflictError(AppError):
    """Usado para transicoes de estado invalidas (HTTP 409)."""

    status_code = 409
    error_code = "conflict"


class RateLimitError(AppError):
    status_code = 429
    error_code = "rate_limited"
