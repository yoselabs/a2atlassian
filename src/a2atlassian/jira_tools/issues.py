"""Jira issue tools — get, search, create, update, delete."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2atlassian.client import AtlassianClient
from a2atlassian.formatter import format_result
from a2atlassian.jira.issues import create_issue, delete_issue, get_issue, search, update_issue

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
    async def jira_get_issue(connection: str, issue_key: str, format: str = "json") -> str:  # noqa: A002
        """Get a Jira issue by key. Returns full issue data including fields and status."""
        client = get_client(connection)
        try:
            result = await get_issue(client, issue_key)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"connection": connection})
        return format_result(result, fmt=format)

    @server.tool()
    async def jira_search(connection: str, jql: str, limit: int = 50, offset: int = 0, format: str = "toon") -> str:  # noqa: A002
        """Search Jira issues using JQL. Returns list of matching issues."""
        client = get_client(connection)
        try:
            result = await search(client, jql, limit=limit, offset=offset)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"connection": connection})
        return format_result(result, fmt=format)

    @server.tool()
    async def jira_get_issue_dev_info(connection: str, issue_key: str) -> str:
        """Get development info (branches, commits, PRs) for a Jira issue.

        Note: Dev info requires the Jira Software dev-status API which is not yet
        supported by atlassian-python-api. This is a placeholder.
        """
        return (
            f"Dev info for {issue_key}: dev info requires Jira Software API — not yet supported. "
            "Use the Jira UI or the /rest/dev-status/latest/issue/detail REST endpoint directly."
        )


def register_write(
    server: FastMCP,
    get_connection: Callable[[str], ConnectionInfo],
    enricher: ErrorEnricher,
) -> None:
    @server.tool()
    async def jira_create_issue(
        connection: str,
        project_key: str,
        summary: str,
        issue_type: str,
        description: str | None = None,
        extra_fields: dict | None = None,
        format: str = "json",  # noqa: A002
    ) -> str:
        """Create a new Jira issue. Accepts project_key, summary, issue_type, optional description and extra_fields dict."""
        conn = get_connection(connection)
        if conn.read_only:
            return enricher.enrich(f"Connection '{connection}' is read-only.", {"connection": connection})
        client = AtlassianClient(conn)
        try:
            result = await create_issue(client, project_key, summary, issue_type, description=description, extra_fields=extra_fields)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"connection": connection})
        return format_result(result, fmt=format)

    @server.tool()
    async def jira_update_issue(connection: str, issue_key: str, fields: dict, format: str = "json") -> str:  # noqa: A002
        """Update fields on an existing Jira issue. Pass a dict of field names to values."""
        conn = get_connection(connection)
        if conn.read_only:
            return enricher.enrich(f"Connection '{connection}' is read-only.", {"connection": connection})
        client = AtlassianClient(conn)
        try:
            result = await update_issue(client, issue_key, fields)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"connection": connection})
        return format_result(result, fmt=format)

    @server.tool()
    async def jira_delete_issue(connection: str, issue_key: str, format: str = "json") -> str:  # noqa: A002
        """Delete a Jira issue by key."""
        conn = get_connection(connection)
        if conn.read_only:
            return enricher.enrich(f"Connection '{connection}' is read-only.", {"connection": connection})
        client = AtlassianClient(conn)
        try:
            result = await delete_issue(client, issue_key)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"connection": connection})
        return format_result(result, fmt=format)
