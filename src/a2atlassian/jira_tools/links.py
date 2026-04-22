"""Jira link tools — get link types, create/remove links, link to epic."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2atlassian.client import AtlassianClient
from a2atlassian.formatter import format_result
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
    async def jira_get_link_types(project: str, format: str = "toon") -> str:  # noqa: A002
        """Get all available issue link types (e.g. Blocks, Duplicate, Relates)."""
        client = get_client(project)
        try:
            result = await get_link_types(client)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"project": project})
        return format_result(result, fmt=format)


def register_write(
    server: FastMCP,
    get_connection: Callable[[str], ConnectionInfo],
    enricher: ErrorEnricher,
) -> None:
    @server.tool()
    async def jira_create_issue_link(
        project: str,
        link_type: str,
        inward_key: str,
        outward_key: str,
        format: str = "json",  # noqa: A002
    ) -> str:
        """Create a link between two Jira issues. Use jira_get_link_types to discover available types."""
        conn = get_connection(project)
        if conn.read_only:
            return enricher.enrich(f"Connection '{project}' is read-only.", {"project": project})
        client = AtlassianClient(conn)
        try:
            result = await create_issue_link(client, link_type, inward_key, outward_key)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"project": project})
        return format_result(result, fmt=format)

    @server.tool()
    async def jira_remove_issue_link(project: str, link_id: str, format: str = "json") -> str:  # noqa: A002
        """Remove an issue link by its ID."""
        conn = get_connection(project)
        if conn.read_only:
            return enricher.enrich(f"Connection '{project}' is read-only.", {"project": project})
        client = AtlassianClient(conn)
        try:
            result = await remove_issue_link(client, link_id)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"project": project})
        return format_result(result, fmt=format)

    @server.tool()
    async def jira_link_to_epic(project: str, issue_key: str, epic_key: str, format: str = "json") -> str:  # noqa: A002
        """Set the parent (epic) of an issue. Uses the parent field."""
        conn = get_connection(project)
        if conn.read_only:
            return enricher.enrich(f"Connection '{project}' is read-only.", {"project": project})
        client = AtlassianClient(conn)
        try:
            result = await link_to_epic(client, issue_key, epic_key)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"project": project})
        return format_result(result, fmt=format)
