"""Jira user tools — get user profile."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2atlassian.formatter import format_result
from a2atlassian.jira.users import get_user_profile

if TYPE_CHECKING:
    from collections.abc import Callable

    from mcp.server.fastmcp import FastMCP

    from a2atlassian.client import AtlassianClient
    from a2atlassian.errors import ErrorEnricher


def register_read(
    server: FastMCP,
    get_client: Callable[[str], AtlassianClient],
    enricher: ErrorEnricher,
) -> None:
    @server.tool()
    async def jira_get_user_profile(connection: str, account_id: str, format: str = "json") -> str:  # noqa: A002
        """Get a Jira user profile by account ID."""
        client = get_client(connection)
        try:
            result = await get_user_profile(client, account_id)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"connection": connection})
        return format_result(result, fmt=format)
