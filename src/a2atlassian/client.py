"""Async Atlassian client — wraps atlassian-python-api with retry and rate limiting."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from requests.exceptions import HTTPError

from a2atlassian.errors import A2AtlassianError, AuthenticationError, RateLimitError, ServerError

if TYPE_CHECKING:
    from collections.abc import Callable

    from a2atlassian.connections import ConnectionInfo


def _lazy_jira():
    """Lazy import to avoid loading atlassian module at import time."""
    from atlassian import Jira  # noqa: PLC0415

    return Jira


class AtlassianClient:
    """Async wrapper around atlassian-python-api Jira client."""

    MAX_RETRIES = 2
    RETRY_BACKOFF: list[float] = [1.0, 3.0]  # noqa: RUF012
    REQUEST_TIMEOUT = 30

    def __init__(self, connection: ConnectionInfo) -> None:
        self.connection = connection
        self._jira_instance: Any | None = None

    @property
    def _jira(self) -> Any:
        """Lazily create the Jira client."""
        if self._jira_instance is None:
            jira_cls = _lazy_jira()
            self._jira_instance = jira_cls(
                url=self.connection.url,
                username=self.connection.email,
                password=self.connection.resolved_token,
                cloud=True,
            )
        return self._jira_instance

    async def _call(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """Call a sync atlassian-python-api method with retry logic."""
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                return await asyncio.to_thread(fn, *args, **kwargs)
            except HTTPError as exc:
                status = getattr(exc.response, "status_code", None)

                if status in (401, 403):
                    msg = f"Authentication failed ({status}): {exc}"
                    raise AuthenticationError(msg) from exc

                if status == 429:
                    if attempt < self.MAX_RETRIES:
                        await asyncio.sleep(self.RETRY_BACKOFF[attempt])
                        continue
                    msg = f"Rate limited after {self.MAX_RETRIES + 1} attempts: {exc}"
                    raise RateLimitError(msg) from exc

                if status is not None and status >= 500:
                    if attempt < self.MAX_RETRIES:
                        await asyncio.sleep(self.RETRY_BACKOFF[attempt])
                        continue
                    msg = f"Server error after {self.MAX_RETRIES + 1} attempts: {exc}"
                    raise ServerError(msg) from exc

                raise

        msg = "Unexpected: retry loop exited without returning or raising"
        raise A2AtlassianError(msg)  # unreachable — loop always raises or returns

    async def validate(self) -> dict:
        """Validate the connection by calling /myself. Returns user info."""
        return await self._call(self._jira.myself)
