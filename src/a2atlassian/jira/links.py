"""Jira link operations — link types, create/remove links."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from a2atlassian.formatter import OperationResult

if TYPE_CHECKING:
    from a2atlassian.client import AtlassianClient


def _extract_link_type(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract key fields from a raw link type."""
    return {
        "id": str(raw.get("id", "")),
        "name": raw.get("name", ""),
        "inward": raw.get("inward", ""),
        "outward": raw.get("outward", ""),
    }


async def get_link_types(client: AtlassianClient) -> OperationResult:
    """Get all issue link types."""
    t0 = time.monotonic()
    data = await client._call(client._jira.get_issue_link_types)
    elapsed = int((time.monotonic() - t0) * 1000)

    # Response may be a list or a dict with "issueLinkTypes" key
    if isinstance(data, list):
        link_types = data
    elif isinstance(data, dict):
        link_types = data.get("issueLinkTypes", [])
    else:
        link_types = []

    return OperationResult(
        name="get_link_types",
        data=[_extract_link_type(lt) for lt in link_types],
        count=len(link_types),
        truncated=False,
        time_ms=elapsed,
    )


async def create_issue_link(
    client: AtlassianClient,
    link_type: str,
    inward_key: str,
    outward_key: str,
) -> OperationResult:
    """Create a link between two issues."""
    t0 = time.monotonic()
    await client._call(
        client._jira.create_issue_link,
        {
            "type": {"name": link_type},
            "inwardIssue": {"key": inward_key},
            "outwardIssue": {"key": outward_key},
        },
    )
    elapsed = int((time.monotonic() - t0) * 1000)

    return OperationResult(
        name="create_issue_link",
        data={
            "link_type": link_type,
            "inward_key": inward_key,
            "outward_key": outward_key,
            "status": "created",
        },
        count=1,
        truncated=False,
        time_ms=elapsed,
    )


async def remove_issue_link(client: AtlassianClient, link_id: str) -> OperationResult:
    """Remove an issue link by ID."""
    t0 = time.monotonic()
    await client._call(client._jira.remove_issue_link, link_id)
    elapsed = int((time.monotonic() - t0) * 1000)

    return OperationResult(
        name="remove_issue_link",
        data={"link_id": link_id, "status": "removed"},
        count=1,
        truncated=False,
        time_ms=elapsed,
    )
