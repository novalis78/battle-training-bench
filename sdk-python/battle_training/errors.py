"""Errors raised by the battle.training client.

The API answers errors as JSON: {"error": "<code>", "hint": "<text>"}.
Some endpoints add a body of their own (a 422 from a version upload or a
ladder enrol carries the smoke-test report that rejected the controller).
"""

from __future__ import annotations

from typing import Any, Optional


class ApiError(Exception):
    """Any non-2xx answer from the API.

    Attributes:
        status: HTTP status code.
        error: the API's error code string (e.g. "name_taken"), if sent.
        hint: the API's human-readable hint, if sent.
        body: the full decoded JSON body, if the answer was JSON.
    """

    def __init__(
        self,
        status: int,
        message: str = "",
        *,
        error: Optional[str] = None,
        hint: Optional[str] = None,
        body: Any = None,
    ) -> None:
        self.status = status
        self.error = error
        self.hint = hint
        self.body = body
        text = message or error or f"HTTP {status}"
        if hint:
            text = f"{text} ({hint})"
        super().__init__(f"[{status}] {text}")


class AuthenticationError(ApiError):
    """401: no key, a bad key, or a key required but not configured."""


class NotFoundError(ApiError):
    """404: the bot, match, ladder or replay does not exist."""


class ValidationError(ApiError):
    """422: the request was understood but rejected on content.

    For version uploads and ladder enrolments the body carries the
    smoke-test report; it is exposed as :attr:`smoke` (alias
    :attr:`report`).
    """

    @property
    def smoke(self) -> Any:
        if isinstance(self.body, dict):
            return self.body.get("smoke")
        return None

    @property
    def report(self) -> Any:
        return self.smoke
