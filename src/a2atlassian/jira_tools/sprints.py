"""Jira sprint tools — get sprints, create, update, add issues."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2atlassian.client import AtlassianClient
from a2atlassian.formatter import format_result
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
    async def jira_get_sprints(connection: str, board_id: int, format: str = "toon") -> str:  # noqa: A002
        """Get all sprints for a Jira board."""
        client = get_client(connection)
        try:
            result = await get_sprints(client, board_id)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"connection": connection})
        return format_result(result, fmt=format)

    @server.tool()
    async def jira_get_sprint_issues(connection: str, sprint_id: int, limit: int = 50, offset: int = 0, format: str = "toon") -> str:  # noqa: A002
        """Get issues in a specific sprint."""
        client = get_client(connection)
        try:
            result = await get_sprint_issues(client, sprint_id, limit=limit, offset=offset)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"connection": connection})
        return format_result(result, fmt=format)


def register_write(
    server: FastMCP,
    get_connection: Callable[[str], ConnectionInfo],
    enricher: ErrorEnricher,
) -> None:
    @server.tool()
    async def jira_create_sprint(
        connection: str,
        name: str,
        board_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        format: str = "json",  # noqa: A002
    ) -> str:
        """Create a new sprint on a Jira board."""
        conn = get_connection(connection)
        if conn.read_only:
            return enricher.enrich(f"Connection '{connection}' is read-only.", {"connection": connection})
        client = AtlassianClient(conn)
        try:
            result = await create_sprint(client, name, board_id, start_date=start_date, end_date=end_date)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"connection": connection})
        return format_result(result, fmt=format)

    @server.tool()
    async def jira_update_sprint(
        connection: str,
        sprint_id: int,
        name: str | None = None,
        state: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        format: str = "json",  # noqa: A002
    ) -> str:
        """Update an existing sprint (name, state, dates)."""
        conn = get_connection(connection)
        if conn.read_only:
            return enricher.enrich(f"Connection '{connection}' is read-only.", {"connection": connection})
        client = AtlassianClient(conn)
        try:
            kwargs = {
                k: v for k, v in {"name": name, "state": state, "start_date": start_date, "end_date": end_date}.items() if v is not None
            }
            result = await update_sprint(client, sprint_id, **kwargs)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"connection": connection})
        return format_result(result, fmt=format)

    @server.tool()
    async def jira_add_issues_to_sprint(connection: str, sprint_id: int, issue_keys: list[str], format: str = "json") -> str:  # noqa: A002
        """Move issues into a sprint."""
        conn = get_connection(connection)
        if conn.read_only:
            return enricher.enrich(f"Connection '{connection}' is read-only.", {"connection": connection})
        client = AtlassianClient(conn)
        try:
            result = await add_issues_to_sprint(client, sprint_id, issue_keys)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"connection": connection})
        return format_result(result, fmt=format)
