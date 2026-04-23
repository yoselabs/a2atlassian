"""Jira field tools — search fields, get field options."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from a2atlassian.decorators import mcp_tool
from a2atlassian.formatter import OperationResult  # noqa: TC001 — FastMCP needs runtime annotation
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
    @mcp_tool(enricher)
    async def jira_search_fields(
        connection: str,
        format: Literal["toon", "json"] = "toon",  # noqa: A002
    ) -> OperationResult:
        """Search all Jira fields. Returns field id, name, custom flag, and schema type.

        Returns TOON by default (compact); pass format='json' for standard JSON shape.
        """
        return await search_fields(get_client(connection))

    @server.tool()
    @mcp_tool(enricher)
    async def jira_get_field_options(
        connection: str,
        field_id: str,
        format: Literal["toon", "json"] = "toon",  # noqa: A002
    ) -> OperationResult:
        """Get allowed values for a Jira field.

        Returns TOON by default (compact); pass format='json' for standard JSON shape.
        """
        return await get_field_options(get_client(connection), field_id)
