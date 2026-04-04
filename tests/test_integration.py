"""Integration tests — verify the full stack wires together correctly."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from a2atlassian.client import AtlassianClient
from a2atlassian.connections import ConnectionInfo
from a2atlassian.formatter import format_result
from a2atlassian.jira.comments import add_comment, edit_comment, get_comments
from a2atlassian.jira.issues import get_issue, search
from a2atlassian.jira.transitions import get_transitions, transition_issue
from a2atlassian.mcp_server import _parse_register_args, _parse_scope_args


@pytest.fixture
def mock_jira_client() -> AtlassianClient:
    conn = ConnectionInfo(
        project="integration",
        url="https://integration.atlassian.net",
        email="test@test.com",
        token="test-token",
        read_only=False,
    )
    client = AtlassianClient(conn)
    client._jira_instance = MagicMock()
    return client


class TestFullWorkflow:
    """Test the secondary critical path: fetch → comment → update comment → transition."""

    async def test_fetch_comment_transition_workflow(self, mock_jira_client: AtlassianClient) -> None:
        jira = mock_jira_client._jira_instance

        # 1. Get issue
        jira.issue.return_value = {
            "key": "PROJ-42",
            "fields": {"summary": "Implement auth", "status": {"name": "To Do"}},
        }
        issue = await get_issue(mock_jira_client, "PROJ-42")
        assert issue.data["key"] == "PROJ-42"

        # 2. Get comments
        jira.issue_get_comments.return_value = {"comments": [], "total": 0}
        comments = await get_comments(mock_jira_client, "PROJ-42")
        assert comments.count == 0

        # 3. Add comment
        jira.issue_add_comment.return_value = {"id": "100", "body": "Starting work"}
        new_comment = await add_comment(mock_jira_client, "PROJ-42", "Starting work")
        assert new_comment.data["id"] == "100"

        # 4. Edit comment (progress update)
        jira.issue_edit_comment.return_value = {"id": "100", "body": "50% done"}
        updated = await edit_comment(mock_jira_client, "PROJ-42", "100", "50% done")
        assert updated.data["body"] == "50% done"

        # 5. Get transitions
        jira.get_issue_transitions.return_value = [
            {"id": "21", "name": "In Progress"},
            {"id": "31", "name": "Done"},
        ]
        transitions = await get_transitions(mock_jira_client, "PROJ-42")
        assert len(transitions.data) == 2

        # 6. Transition
        jira.issue_transition.return_value = None
        result = await transition_issue(mock_jira_client, "PROJ-42", "31")
        assert result.data["transition_id"] == "31"


class TestFormatting:
    async def test_search_toon_format(self, mock_jira_client: AtlassianClient) -> None:
        mock_jira_client._jira_instance.jql.return_value = {
            "issues": [
                {"key": "PROJ-1", "fields": {"summary": "First"}},
                {"key": "PROJ-2", "fields": {"summary": "Second"}},
            ],
            "total": 2,
        }
        result = await search(mock_jira_client, "project = PROJ")
        output = format_result(result, fmt="toon")
        assert "PROJ-1" in output
        assert "PROJ-2" in output

    async def test_get_issue_json_format(self, mock_jira_client: AtlassianClient) -> None:
        mock_jira_client._jira_instance.issue.return_value = {
            "key": "PROJ-1",
            "fields": {"summary": "Test"},
        }
        result = await get_issue(mock_jira_client, "PROJ-1")
        output = format_result(result, fmt="json")
        parsed = json.loads(output)
        assert parsed["data"]["key"] == "PROJ-1"
        assert parsed["time_ms"] >= 0


class TestConnectionScoping:
    def test_register_and_scope_args(self) -> None:
        args = [
            "--register",
            "a",
            "https://a.net",
            "a@m.com",
            "tok_a",
            "--scope",
            "saved_proj",
            "--register",
            "b",
            "https://b.net",
            "b@m.com",
            "tok_b",
            "--rw",
        ]
        registered = _parse_register_args(args)
        scoped = _parse_scope_args(args)

        assert len(registered) == 2
        assert registered[0].read_only is True
        assert registered[1].read_only is False
        assert scoped == ["saved_proj"]
