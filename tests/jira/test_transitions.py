"""Tests for Jira transition operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from a2atlassian.client import AtlassianClient
from a2atlassian.connections import ConnectionInfo
from a2atlassian.formatter import OperationResult
from a2atlassian.jira.transitions import get_transitions, transition_issue


@pytest.fixture
def mock_client() -> AtlassianClient:
    conn = ConnectionInfo(
        connection="test",
        url="https://test.atlassian.net",
        email="t@t.com",
        token="tok",
        read_only=False,
    )
    client = AtlassianClient(conn)
    client._jira_instance = MagicMock()
    return client


class TestGetTransitions:
    async def test_returns_transitions_dict_to(self, mock_client: AtlassianClient) -> None:
        """REST API returns 'to' as a dict with a 'name' key."""
        mock_client._jira_instance.get_issue_transitions.return_value = [
            {"id": "11", "name": "To Do", "to": {"name": "To Do"}},
            {"id": "21", "name": "In Progress", "to": {"name": "In Progress"}},
            {"id": "31", "name": "Done", "to": {"name": "Done"}},
        ]
        result = await get_transitions(mock_client, "PROJ-1")
        assert isinstance(result, OperationResult)
        assert len(result.data) == 3
        assert result.data[0]["name"] == "To Do"
        assert result.data[0]["to_status"] == "To Do"
        assert result.data[0]["id"] == "11"

    async def test_returns_transitions_string_to(self, mock_client: AtlassianClient) -> None:
        """atlassian-python-api returns 'to' as a plain string."""
        mock_client._jira_instance.get_issue_transitions.return_value = [
            {"id": 11, "name": "To Do", "to": "To Do"},
            {"id": 21, "name": "In Progress", "to": "In Progress"},
            {"id": 31, "name": "Done", "to": "Done"},
        ]
        result = await get_transitions(mock_client, "PROJ-1")
        assert len(result.data) == 3
        assert result.data[0]["to_status"] == "To Do"
        assert result.data[0]["id"] == "11"


class TestTransitionIssue:
    async def test_transition_by_id(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.issue_transition.return_value = None
        result = await transition_issue(mock_client, "PROJ-1", "21")
        assert isinstance(result, OperationResult)
        assert result.data["issue_key"] == "PROJ-1"
        assert result.data["transition_id"] == "21"
        mock_client._jira_instance.issue_transition.assert_called_once_with("PROJ-1", "21")
