"""Jira worklog tools — two-mode get (raw + summary) and add."""

from __future__ import annotations

from datetime import date as date_cls
from typing import TYPE_CHECKING, Literal
from zoneinfo import ZoneInfo

from a2atlassian.client import AtlassianClient
from a2atlassian.decorators import mcp_tool
from a2atlassian.formatter import OperationResult
from a2atlassian.jira.worklogs import (
    _parse_started,
    add_worklog,
    get_worklogs,
    get_worklogs_summary,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from mcp.server.fastmcp import FastMCP

    from a2atlassian.connections import ConnectionInfo
    from a2atlassian.errors import ErrorEnricher


def _filter_raw_by_date(
    result: OperationResult,
    tz_name: str,
    date_from: str,
    date_to: str | None,
) -> OperationResult:
    """Filter raw-mode worklogs to a [date_from, date_to] range in the given timezone."""
    tz = ZoneInfo(tz_name)
    dfrom = date_cls.fromisoformat(date_from)
    dto = date_cls.fromisoformat(date_to) if date_to else dfrom

    def in_range(w: dict) -> bool:
        started = w.get("started", "")
        if not started:
            return False
        d = _parse_started(started).astimezone(tz).date()
        return dfrom <= d <= dto

    filtered = [w for w in result.data if in_range(w)]
    return OperationResult(
        name=result.name,
        data=filtered,
        count=len(filtered),
        truncated=False,
        time_ms=result.time_ms,
    )


def register_read(
    server: FastMCP,
    get_client: Callable[[str], AtlassianClient],
    enricher: ErrorEnricher,
) -> None:
    @server.tool()
    @mcp_tool(enricher)
    async def jira_get_worklogs(
        connection: str,
        issue_key: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        people: list[str] | None = None,
        jql_scope: str | None = None,
        detail: Literal["auto", "raw", "total", "by_day", "by_ticket"] = "auto",
        format: Literal["toon", "json"] = "toon",  # noqa: A002
    ) -> OperationResult:
        """Get worklogs for a Jira issue (raw mode) or aggregated across a date range (summary mode).

        Mode selection:
          - issue_key set, date_from unset  → raw mode: per-worklog dump for the ticket.
          - issue_key set, date_from set    → raw mode, filtered to the date range.
          - issue_key unset, date_from set  → summary mode per attribution rules.
          - both unset                      → error.

        detail='auto' resolves to 'raw' when issue_key is set, else 'by_day'.

        Returns TOON by default (compact); pass format='json' for standard JSON shape.
        """
        if not issue_key and not date_from:
            raise ValueError("Provide either issue_key (raw mode) or date_from (summary mode).")

        client = get_client(connection)

        if issue_key:
            result = await get_worklogs(client, issue_key)
            if date_from:
                return _filter_raw_by_date(result, client.connection.timezone, date_from, date_to)
            return result

        # Summary mode. date_from is guaranteed non-None (checked above).
        if date_from is None:  # pragma: no cover — unreachable; checked above
            raise ValueError("Provide either issue_key (raw mode) or date_from (summary mode).")
        summary_detail: Literal["total", "by_day", "by_ticket"]
        if detail in ("auto", "by_day"):
            summary_detail = "by_day"
        elif detail == "total":
            summary_detail = "total"
        elif detail == "by_ticket":
            summary_detail = "by_ticket"
        else:
            raise ValueError("detail='raw' is only valid with issue_key set.")
        return await get_worklogs_summary(
            client,
            date_from=date_from,
            date_to=date_to,
            people=people,
            jql_scope=jql_scope,
            detail=summary_detail,
        )


def register_write(
    server: FastMCP,
    get_connection: Callable[[str], ConnectionInfo],
    enricher: ErrorEnricher,
) -> None:
    @server.tool()
    @mcp_tool(enricher)
    async def jira_add_worklog(
        connection: str,
        issue_key: str,
        time_spent: str,
        comment: str = "",
        format: Literal["toon", "json"] = "json",  # noqa: A002
    ) -> OperationResult:
        """Add a worklog entry to a Jira issue. time_spent is a string like '2h 30m'."""
        conn = get_connection(connection)
        if conn.read_only:
            raise RuntimeError(f"Connection '{connection}' is read-only. Run: a2atlassian login -c {connection} --no-read-only")
        return await add_worklog(AtlassianClient(conn), issue_key, time_spent, comment=comment)
