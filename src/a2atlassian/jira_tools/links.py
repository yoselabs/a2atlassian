"""Jira link tools — get link types, create/remove links, link to epic."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from a2atlassian.client import AtlassianClient
from a2atlassian.decorators import mcp_tool
from a2atlassian.formatter import OperationResult  # noqa: TC001 — FastMCP needs runtime annotation
from a2atlassian.jira.links import create_issue_link, get_link_types, link_to_epic, remove_issue_link

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
    async def jira_get_link_types(
        connection: str,
        format: Literal["toon", "json"] = "toon",  # noqa: A002
    ) -> OperationResult:
        """Get all available issue link types (e.g. Blocks, Duplicate, Relates).

        Returns TOON by default (compact); pass format='json' for standard JSON shape.
        """
        return await get_link_types(get_client(connection))


def register_write(
    server: FastMCP,
    get_connection: Callable[[str], ConnectionInfo],
    enricher: ErrorEnricher,
) -> None:
    @server.tool()
    @mcp_tool(enricher)
    async def jira_create_issue_link(
        connection: str,
        link_type: str,
        inward_key: str,
        outward_key: str,
        format: Literal["toon", "json"] = "json",  # noqa: A002
    ) -> OperationResult:
        """Create a link between two Jira issues. Use jira_get_link_types to discover available types."""
        conn = get_connection(connection)
        if conn.read_only:
            raise RuntimeError(f"Connection '{connection}' is read-only. Run: a2atlassian login -c {connection} --no-read-only")
        return await create_issue_link(AtlassianClient(conn), link_type, inward_key, outward_key)

    @server.tool()
    @mcp_tool(enricher)
    async def jira_remove_issue_link(
        connection: str,
        link_id: str,
        format: Literal["toon", "json"] = "json",  # noqa: A002
    ) -> OperationResult:
        """Remove an issue link by its ID."""
        conn = get_connection(connection)
        if conn.read_only:
            raise RuntimeError(f"Connection '{connection}' is read-only. Run: a2atlassian login -c {connection} --no-read-only")
        return await remove_issue_link(AtlassianClient(conn), link_id)

    @server.tool()
    @mcp_tool(enricher)
    async def jira_link_to_epic(
        connection: str,
        issue_key: str,
        epic_key: str,
        format: Literal["toon", "json"] = "json",  # noqa: A002
    ) -> OperationResult:
        """Set the parent (epic) of an issue. Uses the parent field."""
        conn = get_connection(connection)
        if conn.read_only:
            raise RuntimeError(f"Connection '{connection}' is read-only. Run: a2atlassian login -c {connection} --no-read-only")
        return await link_to_epic(AtlassianClient(conn), issue_key, epic_key)
