"""Jira worklog tools — get and add worklogs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2atlassian.client import AtlassianClient
from a2atlassian.formatter import format_result
from a2atlassian.jira.worklogs import add_worklog, get_worklogs

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
    async def jira_get_worklogs(project: str, issue_key: str, format: str = "toon") -> str:  # noqa: A002
        """Get worklogs for a Jira issue."""
        client = get_client(project)
        try:
            result = await get_worklogs(client, issue_key)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"project": project})
        return format_result(result, fmt=format)


def register_write(
    server: FastMCP,
    get_connection: Callable[[str], ConnectionInfo],
    enricher: ErrorEnricher,
) -> None:
    @server.tool()
    async def jira_add_worklog(
        project: str,
        issue_key: str,
        time_spent: str,
        comment: str = "",
        format: str = "json",  # noqa: A002
    ) -> str:
        """Add a worklog entry to a Jira issue. time_spent is a string like '2h 30m'."""
        conn = get_connection(project)
        if conn.read_only:
            return enricher.enrich(f"Connection '{project}' is read-only.", {"project": project})
        client = AtlassianClient(conn)
        try:
            result = await add_worklog(client, issue_key, time_spent, comment=comment)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"project": project})
        return format_result(result, fmt=format)
