"""Jira sprint tools — get sprints, create, update, add issues."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from a2atlassian.client import AtlassianClient
from a2atlassian.decorators import mcp_tool
from a2atlassian.formatter import OperationResult  # noqa: TC001 — FastMCP needs runtime annotation
from a2atlassian.jira.sprints import add_issues_to_sprint, create_sprint, get_sprint_issues, get_sprints, update_sprint

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
    async def jira_get_sprints(
        connection: str,
        board_id: int,
        format: Literal["toon", "json"] = "toon",  # noqa: A002
    ) -> OperationResult:
        """Get all sprints for a Jira board.

        Returns TOON by default (compact); pass format='json' for standard JSON shape.
        """
        return await get_sprints(get_client(connection), board_id)

    @server.tool()
    @mcp_tool(enricher)
    async def jira_get_sprint_issues(
        connection: str,
        sprint_id: int,
        limit: int = 50,
        offset: int = 0,
        format: Literal["toon", "json"] = "toon",  # noqa: A002
    ) -> OperationResult:
        """Get issues in a specific sprint.

        Returns TOON by default (compact); pass format='json' for standard JSON shape.
        """
        return await get_sprint_issues(get_client(connection), sprint_id, limit=limit, offset=offset)


def register_write(
    server: FastMCP,
    get_connection: Callable[[str], ConnectionInfo],
    enricher: ErrorEnricher,
) -> None:
    @server.tool()
    @mcp_tool(enricher)
    async def jira_create_sprint(
        connection: str,
        name: str,
        board_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        format: Literal["toon", "json"] = "json",  # noqa: A002
    ) -> OperationResult:
        """Create a new sprint on a Jira board."""
        conn = get_connection(connection)
        if conn.read_only:
            raise RuntimeError(f"Connection '{connection}' is read-only. Run: a2atlassian login -c {connection} --no-read-only")
        return await create_sprint(AtlassianClient(conn), name, board_id, start_date=start_date, end_date=end_date)

    @server.tool()
    @mcp_tool(enricher)
    async def jira_update_sprint(
        connection: str,
        sprint_id: int,
        name: str | None = None,
        state: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        format: Literal["toon", "json"] = "json",  # noqa: A002
    ) -> OperationResult:
        """Update an existing sprint (name, state, dates)."""
        conn = get_connection(connection)
        if conn.read_only:
            raise RuntimeError(f"Connection '{connection}' is read-only. Run: a2atlassian login -c {connection} --no-read-only")
        kwargs = {k: v for k, v in {"name": name, "state": state, "start_date": start_date, "end_date": end_date}.items() if v is not None}
        return await update_sprint(AtlassianClient(conn), sprint_id, **kwargs)

    @server.tool()
    @mcp_tool(enricher)
    async def jira_add_issues_to_sprint(
        connection: str,
        sprint_id: int,
        issue_keys: list[str],
        format: Literal["toon", "json"] = "json",  # noqa: A002
    ) -> OperationResult:
        """Move issues into a sprint."""
        conn = get_connection(connection)
        if conn.read_only:
            raise RuntimeError(f"Connection '{connection}' is read-only. Run: a2atlassian login -c {connection} --no-read-only")
        return await add_issues_to_sprint(AtlassianClient(conn), sprint_id, issue_keys)
