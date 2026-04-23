"""Confluence-specific Atlassian client — lazy atlassian.Confluence wrapper."""

from __future__ import annotations

from typing import Any

from a2atlassian.client import AtlassianClientBase


def _lazy_confluence() -> Any:
    """Lazy import to avoid loading atlassian module at import time."""
    from atlassian import Confluence  # noqa: PLC0415

    return Confluence


class ConfluenceClient(AtlassianClientBase):
    """Async wrapper around atlassian-python-api Confluence client."""

    def __init__(self, connection: Any) -> None:
        super().__init__(connection)
        self._confluence_instance: Any | None = None

    @property
    def _confluence(self) -> Any:
        """Lazily create the Confluence client."""
        if self._confluence_instance is None:
            confluence_cls = _lazy_confluence()
            self._confluence_instance = confluence_cls(
                url=self.connection.url,
                username=self.connection.email,
                password=self.connection.resolved_token,
                cloud=True,
            )
        return self._confluence_instance

    async def validate(self) -> dict:
        """Validate the connection by calling the Confluence current-user endpoint.

        Uses the raw REST path because atlassian-python-api's Confluence class
        does not expose a `myself` helper. The endpoint returns
        {accountId, displayName, ...}.
        """
        return await self._call(self._confluence.get, "rest/api/user/current")
