"""Jira board tools — list boards, get board issues."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2atlassian.formatter import format_result
from a2atlassian.jira.boards import get_board_issues, get_boards

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
    async def jira_get_boards(connection: str, format: str = "toon") -> str:  # noqa: A002
        """List all Jira boards visible to the authenticated user."""
        client = get_client(connection)
        try:
            result = await get_boards(client)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"connection": connection})
        return format_result(result, fmt=format)

    @server.tool()
    async def jira_get_board_issues(connection: str, board_id: int, limit: int = 50, offset: int = 0, format: str = "toon") -> str:  # noqa: A002
        """Get issues for a specific Jira board."""
        client = get_client(connection)
        try:
            result = await get_board_issues(client, board_id, limit=limit, offset=offset)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"connection": connection})
        return format_result(result, fmt=format)
