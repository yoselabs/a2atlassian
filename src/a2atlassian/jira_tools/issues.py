"""Jira issue tools — get, search, create, update, delete."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from a2atlassian.client import AtlassianClient
from a2atlassian.decorators import mcp_tool
from a2atlassian.formatter import OperationResult  # noqa: TC001 — FastMCP needs runtime annotation
from a2atlassian.jira.issues import create_issue, delete_issue, get_issue, search, search_count, update_issue

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
    @mcp_tool(enricher)
    async def jira_get_issue(
        connection: str,
        issue_key: str,
        format: Literal["toon", "json"] = "json",  # noqa: A002
    ) -> OperationResult:
        """Get a Jira issue by key. Returns full issue data including fields and status."""
        return await get_issue(get_client(connection), issue_key)

    @server.tool()
    @mcp_tool(enricher)
    async def jira_search(
        connection: str,
        jql: str,
        limit: int = 50,
        offset: int = 0,
        fields: list[str] | None = None,
        format: Literal["toon", "json"] = "toon",  # noqa: A002
    ) -> OperationResult:
        """Search Jira issues using JQL. Returns list of matching issues.

        Default returns a minimal field set (summary/status/assignee/priority/type/parent/updated).
        Pass fields=["*all"] for full payload — can be very large.
        Returns TOON by default (compact); pass format='json' for standard JSON shape.
        """
        return await search(get_client(connection), jql, limit=limit, offset=offset, fields=fields)

    @server.tool()
    @mcp_tool(enricher)
    async def jira_search_count(connection: str, jql: str, format: Literal["toon", "json"] = "json") -> OperationResult:  # noqa: A002
        """Return the total number of Jira issues matching a JQL query. Cheap pre-check before a broad search."""
        return await search_count(get_client(connection), jql)


def register_write(
    server: FastMCP,
    get_connection: Callable[[str], ConnectionInfo],
    enricher: ErrorEnricher,
) -> None:
    @server.tool()
    @mcp_tool(enricher)
    async def jira_create_issue(
        connection: str,
        project_key: str,
        summary: str,
        issue_type: str,
        description: str | None = None,
        extra_fields: dict | None = None,
        format: Literal["toon", "json"] = "json",  # noqa: A002
    ) -> OperationResult:
        """Create a new Jira issue. Accepts project_key, summary, issue_type, optional description and extra_fields dict."""
        conn = get_connection(connection)
        if conn.read_only:
            raise RuntimeError(f"Connection '{connection}' is read-only. Run: a2atlassian login -c {connection} --no-read-only")
        return await create_issue(
            AtlassianClient(conn),
            project_key,
            summary,
            issue_type,
            description=description,
            extra_fields=extra_fields,
        )

    @server.tool()
    @mcp_tool(enricher)
    async def jira_update_issue(
        connection: str,
        issue_key: str,
        fields: dict,
        format: Literal["toon", "json"] = "json",  # noqa: A002
    ) -> OperationResult:
        """Update fields on an existing Jira issue. Pass a dict of field names to values."""
        conn = get_connection(connection)
        if conn.read_only:
            raise RuntimeError(f"Connection '{connection}' is read-only. Run: a2atlassian login -c {connection} --no-read-only")
        return await update_issue(AtlassianClient(conn), issue_key, fields)

    @server.tool()
    @mcp_tool(enricher)
    async def jira_delete_issue(
        connection: str,
        issue_key: str,
        format: Literal["toon", "json"] = "json",  # noqa: A002
    ) -> OperationResult:
        """Delete a Jira issue by key."""
        conn = get_connection(connection)
        if conn.read_only:
            raise RuntimeError(f"Connection '{connection}' is read-only. Run: a2atlassian login -c {connection} --no-read-only")
        return await delete_issue(AtlassianClient(conn), issue_key)
