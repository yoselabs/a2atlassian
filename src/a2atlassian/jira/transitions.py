"""Jira transition operations — get available transitions and transition issues."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from a2atlassian.formatter import OperationResult

if TYPE_CHECKING:
    from a2atlassian.client import AtlassianClient


async def get_transitions(client: AtlassianClient, issue_key: str) -> OperationResult:
    """Get available transitions for a Jira issue."""
    t0 = time.monotonic()
    transitions = await client._call(client._jira.get_issue_transitions, issue_key)
    elapsed = int((time.monotonic() - t0) * 1000)

    return OperationResult(
        name="get_transitions",
        data=transitions,
        count=len(transitions),
        truncated=False,
        time_ms=elapsed,
    )


async def transition_issue(
    client: AtlassianClient,
    issue_key: str,
    transition_id: str,
) -> OperationResult:
    """Transition a Jira issue to a new status."""
    t0 = time.monotonic()
    await client._call(client._jira.issue_transition, issue_key, transition_id)
    elapsed = int((time.monotonic() - t0) * 1000)

    return OperationResult(
        name="transition_issue",
        data={"issue_key": issue_key, "transition_id": transition_id, "status": "transitioned"},
        count=1,
        truncated=False,
        time_ms=elapsed,
    )
