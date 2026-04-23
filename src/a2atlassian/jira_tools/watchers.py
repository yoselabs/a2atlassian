"""Jira watcher tools — get, add, remove watchers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2atlassian.client import AtlassianClient
from a2atlassian.formatter import format_result
from a2atlassian.jira.watchers import add_watcher, get_watchers, remove_watcher

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
    async def jira_get_watchers(connection: str, issue_key: str, format: str = "toon") -> str:  # noqa: A002
        """Get watchers for a Jira issue."""
        client = get_client(connection)
        try:
            result = await get_watchers(client, issue_key)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"connection": connection})
        return format_result(result, fmt=format)


def register_write(
    server: FastMCP,
    get_connection: Callable[[str], ConnectionInfo],
    enricher: ErrorEnricher,
) -> None:
    @server.tool()
    async def jira_add_watcher(connection: str, issue_key: str, account_id: str, format: str = "json") -> str:  # noqa: A002
        """Add a watcher to a Jira issue."""
        conn = get_connection(connection)
        if conn.read_only:
            return enricher.enrich(f"Connection '{connection}' is read-only.", {"connection": connection})
        client = AtlassianClient(conn)
        try:
            result = await add_watcher(client, issue_key, account_id)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"connection": connection})
        return format_result(result, fmt=format)

    @server.tool()
    async def jira_remove_watcher(connection: str, issue_key: str, account_id: str, format: str = "json") -> str:  # noqa: A002
        """Remove a watcher from a Jira issue."""
        conn = get_connection(connection)
        if conn.read_only:
            return enricher.enrich(f"Connection '{connection}' is read-only.", {"connection": connection})
        client = AtlassianClient(conn)
        try:
            result = await remove_watcher(client, issue_key, account_id)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"connection": connection})
        return format_result(result, fmt=format)
