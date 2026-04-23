"""Jira sprint operations — list sprints, sprint issues, create/update sprints."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from a2atlassian.formatter import OperationResult
from a2atlassian.jira.issues import _extract_issue_summary

if TYPE_CHECKING:
    from a2atlassian.client import AtlassianClient


def _extract_sprint(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract key fields from a raw sprint."""
    return {
        "id": str(raw.get("id", "")),
        "name": raw.get("name", ""),
        "state": raw.get("state", ""),
        "start_date": raw.get("startDate", ""),
        "end_date": raw.get("endDate", ""),
    }


async def get_sprints(client: AtlassianClient, board_id: int) -> OperationResult:
    """Get all sprints for a Jira board."""
    t0 = time.monotonic()
    data = await client._call(client._jira.get_all_sprints_from_board, board_id)
    elapsed = int((time.monotonic() - t0) * 1000)

    # Response may be a list or a dict with "values" key
    if isinstance(data, list):
        sprints = data
    elif isinstance(data, dict):
        sprints = data.get("values", data.get("sprints", []))
    else:
        sprints = []

    return OperationResult(
        name="get_sprints",
        data=[_extract_sprint(s) for s in sprints],
        count=len(sprints),
        truncated=False,
        time_ms=elapsed,
    )


async def get_sprint_issues(
    client: AtlassianClient,
    sprint_id: int,
    limit: int = 50,
    offset: int = 0,
) -> OperationResult:
    """Get issues in a sprint."""
    t0 = time.monotonic()
    data = await client._call(
        client._jira.get_sprint_issues,
        sprint_id,
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
        name="get_sprint_issues",
        data=[_extract_issue_summary(i) for i in issues],
        count=len(issues),
        truncated=truncated,
        time_ms=elapsed,
    )


async def create_sprint(
    client: AtlassianClient,
    name: str,
    board_id: int,
    start_date: str | None = None,
    end_date: str | None = None,
) -> OperationResult:
    """Create a new sprint on a board."""
    kwargs: dict[str, Any] = {"name": name, "originBoardId": board_id}
    if start_date:
        kwargs["startDate"] = start_date
    if end_date:
        kwargs["endDate"] = end_date

    t0 = time.monotonic()
    data = await client._call(client._jira.create_sprint, **kwargs)
    elapsed = int((time.monotonic() - t0) * 1000)

    result_data: dict[str, Any]
    if isinstance(data, dict):
        result_data = _extract_sprint(data)
        result_data["status"] = "created"
    else:
        result_data = {"name": name, "board_id": board_id, "status": "created"}

    return OperationResult(
        name="create_sprint",
        data=result_data,
        count=1,
        truncated=False,
        time_ms=elapsed,
    )


async def update_sprint(
    client: AtlassianClient,
    sprint_id: int,
    **kwargs: Any,
) -> OperationResult:
    """Update an existing sprint."""
    t0 = time.monotonic()
    data = await client._call(client._jira.update_partially_sprint, sprint_id, **kwargs)
    elapsed = int((time.monotonic() - t0) * 1000)

    result_data: dict[str, Any]
    if isinstance(data, dict):
        result_data = _extract_sprint(data)
        result_data["status"] = "updated"
    else:
        result_data = {"sprint_id": sprint_id, "status": "updated"}

    return OperationResult(
        name="update_sprint",
        data=result_data,
        count=1,
        truncated=False,
        time_ms=elapsed,
    )


async def add_issues_to_sprint(
    client: AtlassianClient,
    sprint_id: int,
    issue_keys: list[str],
) -> OperationResult:
    """Move issues into a sprint."""
    t0 = time.monotonic()
    await client._call(client._jira.add_issues_to_sprint, sprint_id, issue_keys)
    elapsed = int((time.monotonic() - t0) * 1000)

    return OperationResult(
        name="add_issues_to_sprint",
        data={
            "sprint_id": sprint_id,
            "issue_keys": ", ".join(issue_keys),
            "status": "added",
        },
        count=len(issue_keys),
        truncated=False,
        time_ms=elapsed,
    )
