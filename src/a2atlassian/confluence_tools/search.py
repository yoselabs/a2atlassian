"""Confluence CQL search tool."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from a2atlassian.confluence.search import search as _search
from a2atlassian.decorators import mcp_tool
from a2atlassian.formatter import OperationResult  # noqa: TC001 — FastMCP needs runtime annotation

if TYPE_CHECKING:
    from collections.abc import Callable

    from mcp.server.fastmcp import FastMCP

    from a2atlassian.confluence_client import ConfluenceClient
    from a2atlassian.errors import ErrorEnricher


def register_read(
    server: FastMCP,
    get_client: Callable[[str], ConfluenceClient],
    enricher: ErrorEnricher,
) -> None:
    @server.tool()
    @mcp_tool(enricher)
    async def confluence_search(
        connection: str,
        cql: str,
        limit: int = 25,
        offset: int = 0,
        format: Literal["toon", "json"] = "toon",  # noqa: A002
    ) -> OperationResult:
        """Search Confluence via CQL. Returns minimal row per match.

        Gotcha: `text ~ "..."` in CQL is broad and expensive — prefer `title ~` or
        `space = KEY AND type = page` predicates first.
        """
        return await _search(get_client(connection), cql, limit=limit, offset=offset)
