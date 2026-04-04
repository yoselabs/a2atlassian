"""Jira issue operations — get_issue and search."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from a2atlassian.formatter import OperationResult

if TYPE_CHECKING:
    from a2atlassian.client import AtlassianClient


async def get_issue(client: AtlassianClient, issue_key: str) -> OperationResult:
    """Fetch a single Jira issue by key."""
    t0 = time.monotonic()
    data = await client._call(client._jira.issue, issue_key)
    elapsed = int((time.monotonic() - t0) * 1000)

    return OperationResult(
        name="get_issue",
        data=data,
        count=1,
        truncated=False,
        time_ms=elapsed,
    )


async def search(
    client: AtlassianClient,
    jql: str,
    limit: int = 50,
    offset: int = 0,
) -> OperationResult:
    """Search Jira issues by JQL query."""
    t0 = time.monotonic()
    response = await client._call(
        client._jira.jql,
        jql,
        limit=limit,
        start=offset,
    )
    elapsed = int((time.monotonic() - t0) * 1000)

    issues = response.get("issues", [])
    total = response.get("total", len(issues))
    truncated = total > offset + len(issues) or len(issues) >= limit

    return OperationResult(
        name="search",
        data=issues,
        count=len(issues),
        truncated=truncated,
        time_ms=elapsed,
    )
