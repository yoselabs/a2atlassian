"""Jira comment operations — get, add, edit comments (API v2, wiki markup)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from a2atlassian.formatter import OperationResult

if TYPE_CHECKING:
    from a2atlassian.client import AtlassianClient


async def get_comments(
    client: AtlassianClient,
    issue_key: str,
    limit: int = 50,
    offset: int = 0,
) -> OperationResult:
    """Get comments for a Jira issue."""
    t0 = time.monotonic()
    response = await client._call(client._jira.issue_get_comments, issue_key)
    elapsed = int((time.monotonic() - t0) * 1000)

    comments = response.get("comments", [])
    total = response.get("total", len(comments))

    return OperationResult(
        name="get_comments",
        data=comments,
        count=len(comments),
        truncated=total > len(comments),
        time_ms=elapsed,
    )


async def add_comment(client: AtlassianClient, issue_key: str, body: str) -> OperationResult:
    """Add a comment to a Jira issue. Uses API v2 (wiki markup)."""
    t0 = time.monotonic()
    data = await client._call(client._jira.issue_add_comment, issue_key, body)
    elapsed = int((time.monotonic() - t0) * 1000)

    return OperationResult(
        name="add_comment",
        data=data,
        count=1,
        truncated=False,
        time_ms=elapsed,
    )


async def edit_comment(
    client: AtlassianClient,
    issue_key: str,
    comment_id: str,
    body: str,
) -> OperationResult:
    """Edit an existing comment on a Jira issue. Uses API v2 (wiki markup)."""
    t0 = time.monotonic()
    data = await client._call(client._jira.issue_edit_comment, issue_key, comment_id, body)
    elapsed = int((time.monotonic() - t0) * 1000)

    return OperationResult(
        name="edit_comment",
        data=data,
        count=1,
        truncated=False,
        time_ms=elapsed,
    )
