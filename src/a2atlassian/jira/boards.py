"""Jira board operations — list boards and board issues."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from a2atlassian.formatter import OperationResult
from a2atlassian.jira.issues import _extract_issue_summary

if TYPE_CHECKING:
    from a2atlassian.client import AtlassianClient


def _extract_board(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract key fields from a raw board."""
    board_type = raw.get("type", "")
    # type may be a dict or string
    if isinstance(board_type, dict):
        board_type = board_type.get("name", "")
    else:
        board_type = str(board_type)

    location = raw.get("location") or {}
    if isinstance(location, str):
        project_key = location
    else:
        project_key = location.get("projectKey", "")

    return {
        "id": str(raw.get("id", "")),
        "name": raw.get("name", ""),
        "type": board_type,
        "project_key": project_key,
    }


async def get_boards(
    client: AtlassianClient,
    limit: int = 50,
    offset: int = 0,
) -> OperationResult:
    """List Jira boards."""
    t0 = time.monotonic()
    data = await client._call(client._jira.get_all_agile_boards, startAt=offset, maxResults=limit)
    elapsed = int((time.monotonic() - t0) * 1000)

    # Response may be dict with "values" key or list
    if isinstance(data, list):
        boards = data
        total = len(boards)
    elif isinstance(data, dict):
        boards = data.get("values", [])
        total = data.get("total", len(boards))
    else:
        boards = []
        total = 0

    truncated = total > offset + len(boards) or len(boards) >= limit

    return OperationResult(
        name="get_boards",
        data=[_extract_board(b) for b in boards],
        count=len(boards),
        truncated=truncated,
        time_ms=elapsed,
    )


async def get_board_issues(
    client: AtlassianClient,
    board_id: int,
    limit: int = 50,
    offset: int = 0,
) -> OperationResult:
    """Get issues from a Jira board."""
    t0 = time.monotonic()
    data = await client._call(
        client._jira.get_issues_for_board,
        board_id,
        startAt=offset,
        maxResults=limit,
    )
    elapsed = int((time.monotonic() - t0) * 1000)

    if isinstance(data, dict):
        issues = data.get("issues", [])
        total = data.get("total", len(issues))
    elif isinstance(data, list):
        issues = data
        total = len(issues)
    else:
        issues = []
        total = 0

    truncated = total > offset + len(issues) or len(issues) >= limit

    return OperationResult(
        name="get_board_issues",
        data=[_extract_issue_summary(i) for i in issues],
        count=len(issues),
        truncated=truncated,
        time_ms=elapsed,
    )
