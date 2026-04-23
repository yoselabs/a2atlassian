"""Jira project tools — list projects, versions, components."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2atlassian.client import AtlassianClient
from a2atlassian.formatter import format_result
from a2atlassian.jira.projects import create_version, get_project_components, get_project_versions, get_projects

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
    async def jira_get_projects(connection: str, format: str = "toon") -> str:  # noqa: A002
        """List all Jira projects."""
        client = get_client(connection)
        try:
            result = await get_projects(client)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"connection": connection})
        return format_result(result, fmt=format)

    @server.tool()
    async def jira_get_project_versions(connection: str, project_key: str, format: str = "toon") -> str:  # noqa: A002
        """Get versions for a Jira project."""
        client = get_client(connection)
        try:
            result = await get_project_versions(client, project_key)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"connection": connection})
        return format_result(result, fmt=format)

    @server.tool()
    async def jira_get_project_components(connection: str, project_key: str, format: str = "toon") -> str:  # noqa: A002
        """Get components for a Jira project."""
        client = get_client(connection)
        try:
            result = await get_project_components(client, project_key)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"connection": connection})
        return format_result(result, fmt=format)


def register_write(
    server: FastMCP,
    get_connection: Callable[[str], ConnectionInfo],
    enricher: ErrorEnricher,
) -> None:
    @server.tool()
    async def jira_create_version(connection: str, project_key: str, name: str, format: str = "json") -> str:  # noqa: A002
        """Create a new version in a Jira project."""
        conn = get_connection(connection)
        if conn.read_only:
            return enricher.enrich(f"Connection '{connection}' is read-only.", {"connection": connection})
        client = AtlassianClient(conn)
        try:
            result = await create_version(client, project_key=project_key, name=name)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"connection": connection})
        return format_result(result, fmt=format)
