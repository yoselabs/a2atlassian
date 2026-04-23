"""Jira comment tools — get, add, edit."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2atlassian.client import AtlassianClient
from a2atlassian.formatter import format_result
from a2atlassian.jira.comments import add_comment, edit_comment, get_comments

if TYPE_CHECKING:
    from collections.abc import Callable

    from mcp.server.fastmcp import FastMCP

    from a2atlassian.connections import ConnectionInfo
    from a2atlassian.errors import ErrorEnricher


def register_read(
    server: FastMCP,
    get_client: Callable[[str], AtlassianClient],
    enricher: ErrorEnricher,
) -> None:
    @server.tool()
    async def jira_get_comments(connection: str, issue_key: str, format: str = "toon") -> str:  # noqa: A002
        """Get all comments for a Jira issue."""
        client = get_client(connection)
        try:
            result = await get_comments(client, issue_key)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"connection": connection})
        return format_result(result, fmt=format)


def register_write(
    server: FastMCP,
    get_connection: Callable[[str], ConnectionInfo],
    enricher: ErrorEnricher,
) -> None:
    @server.tool()
    async def jira_add_comment(connection: str, issue_key: str, body: str, format: str = "json") -> str:  # noqa: A002
        """Add a comment to a Jira issue. Uses wiki markup (API v2)."""
        conn = get_connection(connection)
        if conn.read_only:
            return enricher.enrich(f"Connection '{connection}' is read-only.", {"connection": connection})
        client = AtlassianClient(conn)
        try:
            result = await add_comment(client, issue_key, body)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"connection": connection})
        return format_result(result, fmt=format)

    @server.tool()
    async def jira_edit_comment(connection: str, issue_key: str, comment_id: str, body: str, format: str = "json") -> str:  # noqa: A002
        """Edit an existing comment on a Jira issue. Uses wiki markup (API v2)."""
        conn = get_connection(connection)
        if conn.read_only:
            return enricher.enrich(f"Connection '{connection}' is read-only.", {"connection": connection})
        client = AtlassianClient(conn)
        try:
            result = await edit_comment(client, issue_key, comment_id, body)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"connection": connection})
        return format_result(result, fmt=format)
