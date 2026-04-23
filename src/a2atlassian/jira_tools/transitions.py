"""Jira transition tools — get available transitions, transition issue."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from a2atlassian.client import AtlassianClient
from a2atlassian.decorators import mcp_tool
from a2atlassian.formatter import OperationResult  # noqa: TC001 — FastMCP needs runtime annotation
from a2atlassian.jira.transitions import get_transitions, transition_issue

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
    async def jira_get_transitions(
        connection: str,
        issue_key: str,
        format: Literal["toon", "json"] = "toon",  # noqa: A002
    ) -> OperationResult:
        """Get available transitions for a Jira issue.

        Returns TOON by default (compact); pass format='json' for standard JSON shape.
        """
        return await get_transitions(get_client(connection), issue_key)


def register_write(
    server: FastMCP,
    get_connection: Callable[[str], ConnectionInfo],
    enricher: ErrorEnricher,
) -> None:
    @server.tool()
    @mcp_tool(enricher)
    async def jira_transition_issue(
        connection: str,
        issue_key: str,
        transition_id: str,
        format: Literal["toon", "json"] = "json",  # noqa: A002
    ) -> OperationResult:
        """Transition a Jira issue to a new status. Use jira_get_transitions to discover available transitions."""
        conn = get_connection(connection)
        if conn.read_only:
            raise RuntimeError(f"Connection '{connection}' is read-only. Run: a2atlassian login -c {connection} --no-read-only")
        return await transition_issue(AtlassianClient(conn), issue_key, transition_id)
