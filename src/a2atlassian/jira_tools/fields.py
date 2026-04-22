"""Jira field tools — search fields, get field options."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2atlassian.formatter import format_result
from a2atlassian.jira.fields import get_field_options, search_fields

if TYPE_CHECKING:
    from collections.abc import Callable

    from mcp.server.fastmcp import FastMCP

    from a2atlassian.client import AtlassianClient
    from a2atlassian.errors import ErrorEnricher


def register_read(
    server: FastMCP,
    get_client: Callable[[str], AtlassianClient],
    enricher: ErrorEnricher,
) -> None:
    @server.tool()
    async def jira_search_fields(project: str, format: str = "toon") -> str:  # noqa: A002
        """Search all Jira fields. Returns field id, name, custom flag, and schema type."""
        client = get_client(project)
        try:
            result = await search_fields(client)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"project": project})
        return format_result(result, fmt=format)

    @server.tool()
    async def jira_get_field_options(project: str, field_id: str, format: str = "toon") -> str:  # noqa: A002
        """Get allowed values for a Jira field."""
        client = get_client(project)
        try:
            result = await get_field_options(client, field_id)
        except Exception as exc:  # noqa: BLE001
            return enricher.enrich(str(exc), {"project": project})
        return format_result(result, fmt=format)
